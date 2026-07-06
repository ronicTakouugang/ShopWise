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
from concurrent.futures import ThreadPoolExecutor
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
CORS(app, supports_credentials=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


#########################
# Initialisation de la BDD pour les abonnements
#########################
def init_db() -> None:
    """Initialise la base de données SQLite pour les abonnements."""
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
def do_search(query: str) -> list:
    """
    Effectue une recherche de produits à partir d'un mot-clé en utilisant plusieurs scrapers.
    Retourne une liste de produits filtrés et triés par prix.
    Chaque scraper est exécuté de manière isolée pour éviter qu'une erreur ne fasse planter tout le processus.
    """
    amazon_records = []
    glotehlo_records = []
    walmart_records = []
    leclerc_records = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_amazon = executor.submit(scrape_amazon, query)
        future_glotehlo = executor.submit(scrape_glotelho, query)
        future_walmart = executor.submit(scrape_walmart, query)
        future_leclerc = executor.submit(scrape_leclerc, query)
        
        try:
            amazon_records = future_amazon.result()
            if amazon_records is None:
                amazon_records = []
        except Exception as e:
            logging.error("Erreur lors du scraping Amazon pour '%s': %s", query, e)
            amazon_records = []

        try:
            glotehlo_records = future_glotehlo.result()
            if glotehlo_records is None:
                glotehlo_records = []
        except Exception as e:
            logging.error("Erreur lors du scraping Glotelho pour '%s': %s", query, e)
            glotehlo_records = []

        try:
            walmart_records = future_walmart.result()
            if walmart_records is None:
                walmart_records = []
        except Exception as e:
            logging.error("Erreur lors du scraping Walmart pour '%s': %s", query, e)
            walmart_records = []

        try:
            leclerc_records = future_leclerc.result()
            if leclerc_records is None:
                leclerc_records = []
        except Exception as e:
            logging.error("Erreur lors du scraping Leclerc pour '%s': %s", query, e)
            leclerc_records = []

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
        session['email'] = email
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
        price = random.uniform(1000, 10000)
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
    smtp_server = "smtp-relay.sendinblue.com"
    smtp_port = 587
    smtp_username = "gunwaterco@gmail.com"
    smtp_password = "JmYtx390OGUBzWgn"
    from_email = "shopwise@gmail.com"
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
    Envoie un email d'alerte et met à jour la BDD pour chaque produit concerné.
    Retourne la liste des alertes déclenchées.
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
                if current_price < baseline_price:
                    send_email_alert(email, product_url, current_price)
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
