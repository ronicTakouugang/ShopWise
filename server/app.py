import logging
import sqlite3
import random
import math
import smtplib
import re
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor, wait as futures_wait
import pyrebase

# --- Fonctions de scraping
from scrapers.amazon_scraper import scrape_amazon
from scrapers.glotehlo_scraper import scrape_glotelho
from scrapers.walmart_scraper import scrape_walmart
from scrapers.leclerc_scraper import scrape_leclerc

import os
from dotenv import load_dotenv
from utils import normalize_text, extract_price, format_price

load_dotenv()

# --- Configuration de Firebase pour l'authentification ---
firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL")
}

firebase = pyrebase.initialize_app(firebaseConfig)
firebase_auth = firebase.auth()

# --- Configuration de l'application Flask ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-secret-key")

# Configuration des cookies de session
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Mettre à True en production avec HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

CORS(app, supports_credentials=True, origins=["http://localhost:4200"])
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


#########################
# Initialisation de la BDD pour les abonnements
#########################
def init_db() -> None:
    """Initialise la base de données SQLite pour les abonnements, favoris et profil."""
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_url TEXT,
                    initial_price REAL,
                    email TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    description TEXT,
                    price TEXT,
                    imageURL TEXT,
                    productURL TEXT,
                    source TEXT,
                    sourceLogo TEXT,
                    rating TEXT,
                    reviewCount TEXT,
                    UNIQUE(email, productURL)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    email TEXT PRIMARY KEY,
                    display_name TEXT,
                    notifications_enabled INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    productURL TEXT,
                    price REAL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorite_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    name TEXT,
                    UNIQUE(email, name)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorite_list_items (
                    list_id INTEGER,
                    productURL TEXT,
                    FOREIGN KEY(list_id) REFERENCES favorite_lists(id) ON DELETE CASCADE,
                    PRIMARY KEY(list_id, productURL)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS in_app_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    message TEXT,
                    productURL TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read INTEGER DEFAULT 0
                )
            """)
            conn.commit()
        logging.info("Base de données initialisée avec succès.")
    except Exception as e:
        logging.error("Erreur lors de l'initialisation de la BDD: %s", e)


init_db()




def compute_deal_attributes(record: dict, query: str = "") -> dict:
    """Calcule et ajoute les attributs de l'offre et le score de pertinence composite."""
    num_price = extract_price(str(record.get("price", "")))
    # Remplacer Infinity par une valeur numérique finie très élevée pour le JSON
    if num_price == float('inf'):
        record["numeric_price"] = 999999999.0
    else:
        record["numeric_price"] = num_price
    
    # Calcul de la pertinence
    relevance_score = 0
    if query:
        query_words = normalize_text(query).lower().split()
        description = normalize_text(record.get("description", "")).lower()
        
        # 1. Correspondance textuelle (Score de base)
        matches = 0
        for word in query_words:
            if word in description:
                matches += 1
                # Bonus si le mot est au début de la description
                if description.startswith(word):
                    relevance_score += 1.0
        
        # Score basé sur le ratio de mots trouvés
        if query_words:
            relevance_score += (matches / len(query_words)) * 5.0
            
        # 2. Qualité des données (Bonus)
        # Bonus si une image est présente
        if record.get("imageURL") and record.get("imageURL") != "N/A":
            relevance_score += 2.0
            
        # Bonus si le prix est valide (pas infini)
        if num_price != float('inf'):
            relevance_score += 1.5
            
        # 3. Pondération par la source (Optionnel, ex: Amazon souvent plus fiable)
        if record.get("source") == "Amazon":
            relevance_score += 0.5
            
        # 4. Popularité (Bonus)
        popularity = record.get("popularity", 0)
        if popularity > 1000:
            relevance_score += 1.0
        elif popularity > 100:
            relevance_score += 0.5
            
    record["relevance_score"] = round(relevance_score, 2)
    return record


#########################
# Fonction de recherche de produits
#########################
# Délai maximum accordé à un site pour répondre avant qu'on l'écarte de la recherche.
SCRAPER_TIMEOUT_SECONDS = 15


def do_search(query: str) -> list:
    """
    Effectue une recherche de produits à partir d'un mot-clé en utilisant plusieurs scrapers.
    Retourne une liste de produits filtrés et triés par prix.
    Les scrapers tournent en parallèle sous un délai commun : un site lent ou en erreur
    est simplement écarté, sans jamais retarder les résultats des autres sites.
    """
    executor = ThreadPoolExecutor(max_workers=4)
    try:
        futures = {
            executor.submit(scrape_amazon, query): "Amazon",
            executor.submit(scrape_glotelho, query): "Glotelho",
            executor.submit(scrape_walmart, query): "Walmart",
            executor.submit(scrape_leclerc, query): "Leclerc",
        }

        # Un seul délai partagé pour les 4 scrapers en même temps : un site lent
        # ne grignote plus le temps d'attente des autres (contrairement à des
        # future.result(timeout=...) enchaînés un par un).
        done, not_done = futures_wait(futures.keys(), timeout=SCRAPER_TIMEOUT_SECONDS)

        results_by_source = {}
        for future in done:
            source_name = futures[future]
            try:
                records = future.result()
                results_by_source[source_name] = records if records else []
            except Exception as e:
                logging.error("Erreur lors du scraping %s pour '%s': %s", source_name, query, e)
                results_by_source[source_name] = []

        for future in not_done:
            source_name = futures[future]
            logging.warning(
                "Le site %s n'a pas répondu en moins de %ds pour la requête '%s', "
                "il est écarté de cette recherche.", source_name, SCRAPER_TIMEOUT_SECONDS, query
            )
            results_by_source[source_name] = []

        amazon_records = results_by_source.get("Amazon", [])
        glotehlo_records = results_by_source.get("Glotelho", [])
        walmart_records = results_by_source.get("Walmart", [])
        leclerc_records = results_by_source.get("Leclerc", [])
    finally:
        # wait=False : on ne bloque pas la réponse sur un scraper resté accroché en arrière-plan,
        # il se terminera de lui-même et sera simplement ignoré.
        executor.shutdown(wait=False)

    combined_results = amazon_records + glotehlo_records + walmart_records + leclerc_records

    filtered_results = []
    seen_urls = set()
    for record in combined_results:
        try:
            # Suppression du filtrage strict sur le prix pour permettre l'affichage de tous les produits
            # On s'assure juste que les clés minimales existent
            if not record.get("description"):
                continue
            
            product_url = record.get("productURL", "").strip()
            if product_url:
                if product_url in seen_urls:
                    continue
                seen_urls.add(product_url)
            
            record = compute_deal_attributes(record, query)
            filtered_results.append(record)
        except Exception as e:
            logging.warning("Erreur lors du traitement d'un résultat : %s", e)
            continue

    try:
        # Tri par pertinence décroissante d'abord, puis par prix croissant
        sorted_results = sorted(
            filtered_results, 
            key=lambda r: (-r.get("relevance_score", 0), r.get("numeric_price", float('inf')))
        )
        return sorted_results
    except Exception as e:
        logging.error("Erreur lors du tri des résultats : %s", e)
        # En cas d'erreur de tri, retourner les résultats non triés mais fonctionnels
        return filtered_results


#########################
# Endpoints d'authentification
#########################
@app.route('/register', methods=['POST'])
def register():
    """
    Crée un nouvel utilisateur via Firebase.
    Retourne un message de succès ou une erreur.
    """
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400
    try:
        user = firebase_auth.create_user_with_email_and_password(email, password)
        session.permanent = True
        session['email'] = email
        session['idToken'] = user.get('idToken')
        logging.info("Compte créé pour %s", email)
        return jsonify({"message": "Compte créé avec succès.", "email": email})
    except Exception as e:
        error_msg = str(e)
        logging.error("Erreur lors de la création du compte : %s", error_msg)
        if "EMAIL_EXISTS" in error_msg:
            return jsonify({"error": "Un compte avec cet e-mail existe déjà."}), 400
        elif "WEAK_PASSWORD" in error_msg:
            return jsonify({"error": "Le mot de passe est trop faible."}), 400
        elif "INVALID_EMAIL" in error_msg:
            return jsonify({"error": "L'adresse e-mail est mal formatée."}), 400
        return jsonify({"error": "Erreur lors de la création du compte."}), 500


@app.route('/login', methods=['POST'])
def login():
    """
    Connecte un utilisateur en vérifiant ses identifiants via Firebase.
    Stocke l'email et le token dans la session.
    """
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis."}), 400
    try:
        user = firebase_auth.sign_in_with_email_and_password(email, password)
        session.permanent = True
        session['email'] = email
        session['idToken'] = user.get('idToken')
        logging.info("Utilisateur connecté : %s", email)
        return jsonify({"message": "Connexion réussie.", "email": email})
    except Exception as e:
        error_msg = str(e)
        logging.error("Erreur lors de la connexion : %s", error_msg)
        if "EMAIL_NOT_FOUND" in error_msg or "INVALID_PASSWORD" in error_msg or "INVALID_LOGIN_CREDENTIALS" in error_msg:
            return jsonify({"error": "Identifiants incorrects."}), 401
        elif "USER_DISABLED" in error_msg:
            return jsonify({"error": "Ce compte a été désactivé."}), 403
        elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
            return jsonify({"error": "Trop de tentatives. Veuillez réessayer plus tard."}), 429
        return jsonify({"error": "Erreur lors de la connexion."}), 500


@app.route('/logout', methods=['POST'])
def logout():
    """Déconnecte l'utilisateur en effaçant la session."""
    session.clear()
    logging.info("Utilisateur déconnecté.")
    return jsonify({"message": "Déconnexion réussie."})


@app.route('/favorites', methods=['GET'])
def get_favorites():
    """Récupère les favoris de l'utilisateur avec support du tri."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    
    email = session['email']
    sort_by = request.args.get('sort', 'date_added') # default sort
    
    query = "SELECT * FROM favorites WHERE email = ?"
    
    # Le tri par date d'ajout n'est pas directement supporté car on n'a pas de colonne date_added
    # On pourrait l'ajouter, mais pour l'instant on trie par ID (qui suit l'ordre d'ajout)
    if sort_by == 'price_asc':
        # Note: price est stocké sous forme de chaîne avec le symbole €, 
        # il faudrait idéalement une colonne numérique pour un tri robuste.
        # Pour l'instant on fait un tri simple.
        query += " ORDER BY CAST(REPLACE(REPLACE(price, '€', ''), ',', '.') AS REAL) ASC"
    elif sort_by == 'price_desc':
        query += " ORDER BY CAST(REPLACE(REPLACE(price, '€', ''), ',', '.') AS REAL) DESC"
    else:
        query += " ORDER BY id DESC" # Date d'ajout (approximé par l'ID)

    try:
        with sqlite3.connect("subscriptions.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (email,))
            rows = cursor.fetchall()
            favorites = [dict(row) for row in rows]
            return jsonify(favorites)
    except Exception as e:
        logging.error("Erreur lors de la récupération des favoris: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/price_history', methods=['GET'])
def get_price_history():
    """Récupère l'historique des prix pour un produit."""
    productURL = request.args.get('productURL')
    if not productURL:
        return jsonify({"error": "productURL requis"}), 400
    
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT price, date 
                FROM price_history 
                WHERE productURL = ? 
                ORDER BY date ASC
            """, (productURL,))
            rows = cursor.fetchall()
            return jsonify([dict(row) for row in rows])
    except Exception as e:
        logging.error("Erreur lors de la récupération de l'historique: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/lists', methods=['GET'])
def get_lists():
    if 'email' not in session: return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM favorite_lists WHERE email = ?", (email,))
            return jsonify([dict(row) for row in cursor.fetchall()])
    except Exception as e: return jsonify({"error": str(e)}), 500


@app.route('/lists', methods=['POST'])
def create_list():
    if 'email' not in session: return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    name = request.json.get('name')
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO favorite_lists (email, name) VALUES (?, ?)", (email, name))
            conn.commit()
            return jsonify({"id": cursor.lastrowid, "name": name})
    except Exception as e: return jsonify({"error": str(e)}), 500


@app.route('/lists/<int:list_id>/items', methods=['POST'])
def add_to_list(list_id):
    if 'email' not in session: return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    productURL = request.json.get('productURL')
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM favorite_lists WHERE id = ? AND email = ?", (list_id, email))
            if not cursor.fetchone():
                return jsonify({"error": "Liste introuvable."}), 404
            cursor.execute("INSERT INTO favorite_list_items (list_id, productURL) VALUES (?, ?)", (list_id, productURL))
            conn.commit()
            return jsonify({"message": "Ajouté à la liste"})
    except Exception as e: return jsonify({"error": str(e)}), 500


@app.route('/notifications', methods=['GET'])
def get_notifications():
    if 'email' not in session: return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM in_app_notifications WHERE email = ? ORDER BY date DESC", (email,))
            return jsonify([dict(row) for row in cursor.fetchall()])
    except Exception as e: return jsonify({"error": str(e)}), 500


@app.route('/notifications/read', methods=['POST'])
def mark_notifications_read():
    """Marque toutes les notifications de l'utilisateur comme lues."""
    if 'email' not in session: return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE in_app_notifications SET is_read = 1 WHERE email = ? AND is_read = 0", (email,))
            conn.commit()
        return jsonify({"message": "Notifications marquées comme lues."})
    except Exception as e: return jsonify({"error": str(e)}), 500


@app.route('/favorites', methods=['POST'])
def add_favorite():
    """Ajoute un produit aux favoris."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    
    email = session['email']
    data = request.json
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO favorites 
                (email, description, price, imageURL, productURL, source, sourceLogo, rating, reviewCount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email, 
                data.get('description'), 
                data.get('price'), 
                data.get('imageURL'), 
                data.get('productURL'), 
                data.get('source'), 
                data.get('sourceLogo'), 
                data.get('rating'), 
                data.get('reviewCount')
            ))
            
            # Ajouter à l'historique des prix lors de l'ajout en favori
            num_price = extract_price(str(data.get('price')))
            if num_price != float('inf'):
                cursor.execute("INSERT INTO price_history (productURL, price) VALUES (?, ?)", (data.get('productURL'), num_price))
            
            conn.commit()
        return jsonify({"message": "Favori ajouté avec succès."})
    except Exception as e:
        logging.error("Erreur lors de l'ajout du favori: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/favorites/remove', methods=['POST'])
def remove_favorite():
    """Supprime un produit des favoris."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    
    email = session['email']
    productURL = request.json.get('productURL')
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM favorites WHERE email = ? AND productURL = ?", (email, productURL))
            conn.commit()
        return jsonify({"message": "Favori supprimé avec succès."})
    except Exception as e:
        logging.error("Erreur lors de la suppression du favori: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/profile', methods=['GET'])
def get_profile():
    """Récupère le profil de l'utilisateur."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    
    email = session['email']
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profile WHERE email = ?", (email,))
            row = cursor.fetchone()
            if row:
                return jsonify(dict(row))
            else:
                # Créer un profil par défaut si inexistant
                display_name = email.split('@')[0]
                cursor.execute("INSERT INTO user_profile (email, display_name) VALUES (?, ?)", (email, display_name))
                conn.commit()
                return jsonify({"email": email, "display_name": display_name, "notifications_enabled": 1})
    except Exception as e:
        logging.error("Erreur lors de la récupération du profil: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/profile', methods=['POST'])
def update_profile():
    """Met à jour le profil de l'utilisateur."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    
    email = session['email']
    data = request.json
    display_name = data.get('display_name')
    notifications_enabled = 1 if data.get('notifications_enabled') else 0
    
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_profile (email, display_name, notifications_enabled)
                VALUES (?, ?, ?)
            """, (email, display_name, notifications_enabled))
            conn.commit()
        return jsonify({"message": "Profil mis à jour avec succès."})
    except Exception as e:
        logging.error("Erreur lors de la mise à jour du profil: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/status', methods=['GET'])
def get_status():
    """Vérifie si l'utilisateur est connecté via la session."""
    if 'email' in session:
        return jsonify({
            "isAuth": True,
            "email": session['email']
        })
    return jsonify({"isAuth": False}), 200


@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    """Envoie un email de réinitialisation de mot de passe via Firebase."""
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email requis."}), 400
    try:
        firebase_auth.send_password_reset_email(email)
        logging.info("Email de réinitialisation envoyé à %s", email)
        return jsonify({"message": "Email de réinitialisation envoyé."})
    except Exception as e:
        logging.error("Erreur lors de la réinitialisation du mot de passe : %s", e)
        return jsonify({"error": "Erreur lors de l'envoi de l'email."}), 500


def mark_favorites(results: list, email: str | None) -> list:
    """Ajoute isFavorite=True aux résultats déjà présents dans les favoris de l'utilisateur."""
    if not email or not results:
        return results
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT productURL FROM favorites WHERE email = ?", (email,))
            favorite_urls = {row[0] for row in cursor.fetchall()}
        for record in results:
            record["isFavorite"] = record.get("productURL") in favorite_urls
    except Exception as e:
        logging.error("Erreur lors du marquage des favoris: %s", e)
    return results


#########################
# Endpoint /search : Recherche de produits
#########################
@app.route('/search', methods=['GET'])
def search():
    """
    Recherche des produits selon un mot-clé.
    Stocke la requête dans la session pour usage ultérieur dans /subscribe.
    """
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Veuillez fournir un mot-clé via le paramètre 'query'."}), 400
    session["last_search_query"] = query
    try:
        results = do_search(query)
        results = mark_favorites(results, session.get("email"))
        logging.info("Recherche '%s' retournant %d résultats.", query, len(results))
        return jsonify(results)
    except Exception as e:
        logging.error("Erreur dans /search: %s", e)
        return jsonify({"error": str(e)}), 500


#########################
# Endpoint /subscribe : Abonnement aux produits de la dernière recherche
#########################
@app.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Enregistre un abonnement pour un query donné.
    Nécessite que l'email soit présent dans la session (login requis)
    et que le query soit envoyé dans le corps de la requête.
    Exemple du corps JSON : {"query": "macbook"}
    """
    data = request.get_json()
    query = data.get("query") if data else None
    email = session.get("email")
    if not query or not email:
        return jsonify({"error": "L'email en session et le query en paramètre sont requis (login et query requis)."}), 400
    try:
        results = do_search(query)
        if not results:
            return jsonify({"message": "Aucun produit trouvé pour la requête."}), 404

        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            count = 0
            for record in results:
                product_url = record.get("productURL", "").strip()
                initial_price = record.get("numeric_price", extract_price(str(record.get("price", ""))))
                if product_url and initial_price != float('inf'):
                    cursor.execute("INSERT INTO subscriptions (product_url, initial_price, email) VALUES (?, ?, ?)",
                                   (product_url, initial_price, email))
                    count += 1
            conn.commit()
        logging.info("Abonnement enregistré pour le query '%s' pour %s (%d produits).", query, email, count)
        return jsonify({"message": f"Abonnement enregistré pour {count} produits.", "count": count})
    except Exception as e:
        logging.error("Erreur dans /subscribe: %s", e)
        return jsonify({"error": str(e)}), 500

#########################
# Fonction de simulation du prix actuel d'un produit
#########################
def get_current_price(product_url: str) -> float:
    """
    Simule la récupération du prix actuel d'un produit.
    Pour une application réelle, implémentez la logique de scraping ou d'API.
    """
    try:
        # Simulation d'un prix en Euro raisonnable (entre 10 et 500)
        price = random.uniform(10, 500)
        return price
    except Exception as e:
        logging.error("Erreur lors de la simulation du prix pour '%s': %s", product_url, e)
        return float('inf')


#########################
# Fonction d'envoi d'email d'alerte
#########################
def send_email_alert(email: str, product_url: str, current_price: float) -> None:
    """
    Envoie un email d'alerte lorsque le prix d'un produit a baissé.
    Utilise le serveur SMTP de Sendinblue.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL")
    if not all([smtp_server, smtp_username, smtp_password, from_email]):
        logging.error("Configuration SMTP manquante : impossible d'envoyer l'email d'alerte.")
        return
    subject = "Alerte: Le prix de votre produit a baissé!"
    body = (f"Bonjour,\n\nLe prix de l'article suivant a baissé : {product_url}\n"
            f"Nouveau prix : {format_price(current_price)}\n\nCordialement,\nVotre équipe")
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        logging.info("Email envoyé à %s", email)
    except Exception as e:
        logging.error("Erreur lors de l'envoi de l'email à %s: %s", email, e)


#########################
# Fonction de vérification des prix et mise à jour des abonnements
#########################
def run_price_check() -> list:
    """
    Vérifie si le prix des produits abonnés a baissé.
    Envoie un email d'alerte, une notification in-app et met à jour la BDD.
    """
    try:
        with sqlite3.connect("subscriptions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, product_url, initial_price, email FROM subscriptions")
            subscriptions = cursor.fetchall()
            alerts_triggered = []
            for sub in subscriptions:
                sub_id, product_url, baseline_price, email = sub
                current_price = get_current_price(product_url)
                
                # Enregistrer systématiquement dans l'historique
                cursor.execute("INSERT INTO price_history (productURL, price) VALUES (?, ?)", (product_url, current_price))
                
                if current_price < baseline_price:
                    # Alerte Email
                    send_email_alert(email, product_url, current_price)
                    
                    # Alerte In-App
                    message = f"Le prix du produit a baissé à {format_price(current_price)} !"
                    cursor.execute("""
                        INSERT INTO in_app_notifications (email, message, productURL)
                        VALUES (?, ?, ?)
                    """, (email, message, product_url))
                    
                    alerts_triggered.append({
                        "subscription_id": sub_id,
                        "email": email,
                        "product_url": product_url,
                        "current_price": format_price(current_price),
                        "previous_price": format_price(baseline_price)
                    })
                    cursor.execute("UPDATE subscriptions SET initial_price = ? WHERE id = ?", (current_price, sub_id))
            conn.commit()
        logging.info("Vérification terminée. Alertes déclenchées : %s", alerts_triggered)
        return alerts_triggered
    except Exception as e:
        logging.error("Erreur lors de la vérification des prix: %s", e)
        return []


@app.route('/check_prices', methods=['GET'])
def check_prices():
    """
    Endpoint manuel pour vérifier les prix des produits abonnés.
    Retourne un message et la liste des articles dont le prix a changé.
    """
    alerts = run_price_check()
    if alerts is None:
        return jsonify({"error": "Erreur lors de la vérification des prix."}), 500
    return jsonify({
        "message": "Vérification manuelle effectuée. Consultez les logs pour plus d'informations.",
        "alerts_triggered": alerts
    })


#########################
# Lancement de l'application et du job planifié
#########################
if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=run_price_check, trigger="interval", hours=2)
    scheduler.start()
    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
