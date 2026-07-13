"""
Point d'entrée de l'application Flask : configuration, routes HTTP et
planification du job périodique de vérification des prix.

Ce fichier contient encore, pour l'instant (Phase 1 du refactoring), la logique
métier (recherche, alertes de prix) directement dans les routes. Cette logique
sera extraite vers services/ en Phase 2. En revanche, plus aucun SQL direct
n'apparaît ici : tout accès à la base passe par repositories/.
"""
import logging
import os
import smtplib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait as futures_wait
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request, session
from flask_cors import CORS

import config
from database import initialize_database
from repositories import (
    articles_repository,
    favorites_repository,
    lists_repository,
    notifications_repository,
    price_history_repository,
    profile_repository,
    search_log_repository,
    subscriptions_repository,
)
from scrapers.amazon_scraper import scrape_amazon
from scrapers.auchan_scraper import scrape_auchan
from scrapers.glotehlo_scraper import scrape_glotelho
from scrapers.leclerc_scraper import scrape_leclerc
from scrapers.walmart_scraper import scrape_walmart
from utils import extract_price, format_price, normalize_text

firebase_auth = config.create_firebase_auth()

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

# Configuration des cookies de session
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Mettre à True en production avec HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

CORS(app, supports_credentials=True, origins=config.CORS_ALLOWED_ORIGINS)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

initialize_database()


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
# Persistance du catalogue d'articles et de l'historique de prix
#########################
def persist_articles(records: list) -> None:
    """
    Met à jour le catalogue d'articles et enregistre un point d'historique de prix
    pour chaque produit ramené par une recherche réelle (hors cache).
    Un nouveau point n'est ajouté à price_history que si le prix a changé par
    rapport au dernier point connu, pour éviter de saturer l'historique de points
    identiques à chaque recherche.
    """
    try:
        for record in records:
            product_url = str(record.get("productURL", "")).strip()
            numeric_price = record.get("numeric_price", float('inf'))
            if not product_url or numeric_price == float('inf'):
                continue
            if numeric_price <= 0 or numeric_price > articles_repository.MAX_PLAUSIBLE_PRICE_EUR:
                logging.warning(
                    "Prix invraisemblable ignoré pour '%s' (%s): %s",
                    record.get("description"), product_url, numeric_price
                )
                continue

            articles_repository.upsert_article(
                product_url,
                record.get("description"),
                record.get("imageURL"),
                record.get("source"),
                record.get("sourceLogo"),
                record.get("rating"),
                record.get("reviewCount"),
                numeric_price,
            )

            last_price = price_history_repository.get_last_price_point(product_url)
            if last_price is None or last_price != numeric_price:
                price_history_repository.insert_price_point(product_url, numeric_price)
    except Exception as e:
        logging.error("Erreur lors de la persistance des articles: %s", e)


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
    executor = ThreadPoolExecutor(max_workers=5)
    try:
        futures = {
            executor.submit(scrape_amazon, query): "Amazon",
            executor.submit(scrape_glotelho, query): "Glotelho",
            executor.submit(scrape_walmart, query): "Walmart",
            executor.submit(scrape_leclerc, query): "Leclerc",
            executor.submit(scrape_auchan, query): "Auchan",
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
        auchan_records = results_by_source.get("Auchan", [])
    finally:
        # wait=False : on ne bloque pas la réponse sur un scraper resté accroché en arrière-plan,
        # il se terminera de lui-même et sera simplement ignoré.
        executor.shutdown(wait=False)

    combined_results = amazon_records + glotehlo_records + walmart_records + leclerc_records + auchan_records

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
    except Exception as e:
        logging.error("Erreur lors du tri des résultats : %s", e)
        # En cas d'erreur de tri, retourner les résultats non triés mais fonctionnels
        sorted_results = filtered_results

    persist_articles(sorted_results)
    return sorted_results


#########################
# Cache court des résultats de recherche
#########################
# Réduit le nombre de requêtes réellement envoyées aux sites pour des recherches
# identiques/répétées (moins de volume = moins de risque de blocage), sans jamais
# ralentir une recherche : un cache "hit" est immédiat, un "miss" se comporte
# exactement comme avant.
SEARCH_CACHE_TTL_SECONDS = 600  # 10 minutes
_search_cache = {}
_search_cache_lock = threading.Lock()


def log_search(query: str) -> None:
    """Enregistre une recherche pour les statistiques (recherches les plus fréquentes)."""
    try:
        search_log_repository.insert_search_log(normalize_text(query), session.get("email"))
    except Exception as e:
        logging.error("Erreur lors de l'enregistrement de la recherche: %s", e)


def do_search_cached(query: str) -> list:
    """Sert les résultats depuis un cache court si disponible, sinon lance do_search."""
    cache_key = normalize_text(query)
    now = time.time()
    log_search(query)

    with _search_cache_lock:
        cached = _search_cache.get(cache_key)
        if cached and (now - cached[0]) < SEARCH_CACHE_TTL_SECONDS:
            logging.info("Résultats servis depuis le cache pour '%s'.", query)
            return cached[1]

    results = do_search(query)

    with _search_cache_lock:
        _search_cache[cache_key] = (now, results)

    return results


#########################
# Endpoints d'authentification
#########################
@app.route('/register', methods=['POST'])
def register():
    """
    Crée un nouvel utilisateur via Firebase.
    Retourne un message de succès ou une erreur.
    """
    registration_payload = request.get_json()
    email = registration_payload.get("email", "").strip()
    password = registration_payload.get("password")
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
    login_payload = request.get_json()
    email = login_payload.get("email", "").strip()
    password = login_payload.get("password")
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
    sort_by = request.args.get('sort', 'date_added')

    try:
        favorites = favorites_repository.get_favorites_by_email(email, sort_by)
        return jsonify(favorites)
    except Exception as e:
        logging.error("Erreur lors de la récupération des favoris: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/price_history', methods=['GET'])
def get_price_history():
    """Récupère l'historique des prix pour un produit."""
    product_url = request.args.get('productURL')
    if not product_url:
        return jsonify({"error": "productURL requis"}), 400

    try:
        return jsonify(price_history_repository.get_price_history(product_url))
    except Exception as e:
        logging.error("Erreur lors de la récupération de l'historique: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """
    Statistiques globales : recherches les plus fréquentes, comparatif agrégé par source
    (prix moyen/min/max), baisses de prix récentes et nombre de produits suivis.
    Ce n'est PAS un comparatif produit-à-produit entre retailers (les résultats de sources
    différentes ne sont pas mis en correspondance par SKU/EAN), juste des stats par source.
    """
    try:
        return jsonify({
            "top_searches": search_log_repository.get_top_searches(limit=10),
            "source_stats": articles_repository.get_price_stats_by_source(),
            "recent_price_drops": notifications_repository.count_recent_notifications(days=7),
            "tracked_subscriptions": subscriptions_repository.count_subscriptions(),
            "tracked_favorites": favorites_repository.count_distinct_favorited_products(),
        })
    except Exception as e:
        logging.error("Erreur lors du calcul des statistiques analytics: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/lists', methods=['GET'])
def get_lists():
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    try:
        return jsonify(lists_repository.get_lists_by_email(session['email']))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/lists', methods=['POST'])
def create_list():
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    name = request.json.get('name')
    try:
        list_id = lists_repository.create_list(email, name)
        return jsonify({"id": list_id, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/lists/<int:list_id>/items', methods=['POST'])
def add_to_list(list_id):
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    product_url = request.json.get('productURL')
    try:
        if not lists_repository.list_belongs_to_email(list_id, email):
            return jsonify({"error": "Liste introuvable."}), 404
        lists_repository.add_item_to_list(list_id, product_url)
        return jsonify({"message": "Ajouté à la liste"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/notifications', methods=['GET'])
def get_notifications():
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    try:
        return jsonify(notifications_repository.get_notifications_by_email(session['email']))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/notifications/read', methods=['POST'])
def mark_notifications_read():
    """Marque toutes les notifications de l'utilisateur comme lues."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    try:
        notifications_repository.mark_all_notifications_read(session['email'])
        return jsonify({"message": "Notifications marquées comme lues."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/favorites', methods=['POST'])
def add_favorite():
    """Ajoute un produit aux favoris."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401

    email = session['email']
    favorite_payload = request.json
    try:
        favorites_repository.upsert_favorite(email, favorite_payload)

        # Ajouter à l'historique des prix lors de l'ajout en favori
        numeric_price = extract_price(str(favorite_payload.get('price')))
        if numeric_price != float('inf'):
            price_history_repository.insert_price_point(favorite_payload.get('productURL'), numeric_price)

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
    product_url = request.json.get('productURL')
    try:
        favorites_repository.delete_favorite(email, product_url)
        return jsonify({"message": "Favori supprimé avec succès."})
    except Exception as e:
        logging.error("Erreur lors de la suppression du favori: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/profile', methods=['GET'])
def get_profile():
    """Récupère le profil de l'utilisateur (le crée avec des valeurs par défaut si inexistant)."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401

    email = session['email']
    try:
        profile = profile_repository.get_profile_by_email(email)
        if profile:
            return jsonify(dict(profile))

        display_name = email.split('@')[0]
        profile_repository.create_default_profile(email, display_name)
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
    profile_payload = request.json
    display_name = profile_payload.get('display_name')
    notifications_enabled = 1 if profile_payload.get('notifications_enabled') else 0

    try:
        profile_repository.upsert_profile(email, display_name, notifications_enabled)
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
    forgot_password_payload = request.get_json()
    email = forgot_password_payload.get("email")
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
    """
    Retourne une copie des résultats avec isFavorite=True pour ceux déjà en favoris.
    On copie chaque enregistrement (au lieu de muter les objets reçus) car `results`
    peut être la liste partagée par le cache de recherche : sans copie, le marquage
    des favoris d'un utilisateur fuiterait vers les autres utilisateurs via le cache.
    """
    copies = [dict(r) for r in results]
    if not email:
        return copies
    try:
        favorite_urls = favorites_repository.get_favorite_urls_by_email(email)
        for record in copies:
            record["isFavorite"] = record.get("productURL") in favorite_urls
    except Exception as e:
        logging.error("Erreur lors du marquage des favoris: %s", e)
    return copies


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
        results = do_search_cached(query)
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
    Exemple du corps JSON : {"query": "macbook", "threshold_percent": 10}
    threshold_percent est optionnel : absent ou null = alerte dès la moindre baisse
    (comportement historique). Sinon, l'alerte n'est déclenchée que si la baisse
    atteint au moins ce pourcentage.
    """
    subscribe_payload = request.get_json()
    query = subscribe_payload.get("query") if subscribe_payload else None
    email = session.get("email")
    threshold_percent = subscribe_payload.get("threshold_percent") if subscribe_payload else None
    if threshold_percent is not None:
        try:
            threshold_percent = float(threshold_percent)
            if threshold_percent <= 0:
                threshold_percent = None
        except (TypeError, ValueError):
            threshold_percent = None
    if not query or not email:
        return jsonify({"error": "L'email en session et le query en paramètre sont requis (login et query requis)."}), 400
    try:
        results = do_search_cached(query)
        if not results:
            return jsonify({"message": "Aucun produit trouvé pour la requête."}), 404

        subscribed_count = 0
        for record in results:
            product_url = record.get("productURL", "").strip()
            initial_price = record.get("numeric_price", extract_price(str(record.get("price", ""))))
            if product_url and initial_price != float('inf'):
                subscriptions_repository.insert_subscription(product_url, email, initial_price, threshold_percent)
                subscribed_count += 1

        logging.info("Abonnement enregistré pour le query '%s' pour %s (%d produits).", query, email, subscribed_count)
        return jsonify({"message": f"Abonnement enregistré pour {subscribed_count} produits.", "count": subscribed_count})
    except Exception as e:
        logging.error("Erreur dans /subscribe: %s", e)
        return jsonify({"error": str(e)}), 500


#########################
# Fonction de récupération du prix actuel d'un produit
#########################
# Sources pour lesquelles on relance un vrai scraping lors du price-check automatique.
# Amazon/Walmart en sont exclus : ce sont des sites déjà sujets au rate-limit (cf. timeouts
# de scraping), et relancer une recherche complète par produit abonné toutes les 2h y
# ajouterait trop de volume. Pour ces deux sources, on se contente du dernier prix connu
# (mis à jour uniquement quand l'utilisateur relance une recherche manuelle).
_LIVE_RECHECK_SCRAPERS = {
    "Glotehlo": scrape_glotelho,
    "E.Leclerc": scrape_leclerc,
    "Auchan": scrape_auchan,
}


def get_current_price(product_url: str) -> float:
    """
    Récupère le prix actuel d'un produit abonné.
    - Glotelho/Leclerc/Auchan : relance une recherche par mot-clé (le nom du produit) et
      retrouve la ligne correspondant à productURL pour en extraire le prix réel.
    - Amazon/Walmart/autre : retourne le dernier prix connu (articles.last_price), sans
      relancer de scraping automatique.
    - Si le produit n'est pas retrouvé (ex: disparu du site), retourne aussi last_price
      pour ne pas déclencher de fausse alerte de baisse.
    """
    try:
        article = articles_repository.get_article_by_url(product_url)
        if article is None:
            return float('inf')

        last_price = article["last_price"] if article["last_price"] is not None else float('inf')
        scraper = _LIVE_RECHECK_SCRAPERS.get(article["source"])
        if scraper is None or not article["description"]:
            return last_price

        records = scraper(article["description"]) or []
        for record in records:
            if str(record.get("productURL", "")).strip() == product_url:
                price = extract_price(str(record.get("price", "")))
                return price if price != float('inf') else last_price

        return last_price
    except Exception as e:
        logging.error("Erreur lors de la récupération du prix pour '%s': %s", product_url, e)
        return float('inf')


#########################
# Fonction d'envoi d'email d'alerte
#########################
def send_email_alert(email: str, product_url: str, current_price: float) -> None:
    """
    Envoie un email d'alerte lorsque le prix d'un produit a baissé.
    Utilise le serveur SMTP configuré (voir config.py).
    """
    if not all([config.SMTP_SERVER, config.SMTP_USERNAME, config.SMTP_PASSWORD, config.SMTP_FROM_EMAIL]):
        logging.error("Configuration SMTP manquante : impossible d'envoyer l'email d'alerte.")
        return
    subject = "Alerte: Le prix de votre produit a baissé!"
    body = (f"Bonjour,\n\nLe prix de l'article suivant a baissé : {product_url}\n"
            f"Nouveau prix : {format_price(current_price)}\n\nCordialement,\nVotre équipe")
    message = MIMEMultipart()
    message["From"] = config.SMTP_FROM_EMAIL
    message["To"] = email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.send_message(message)
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
        alerts_triggered = []
        for subscription in subscriptions_repository.get_all_subscriptions():
            sub_id, product_url, baseline_price, email, threshold_percent = subscription
            current_price = get_current_price(product_url)
            if current_price == float('inf'):
                # Produit introuvable (pas encore dans articles, ou disparu) : on ignore
                # ce tour plutôt que de polluer l'historique avec un prix invalide.
                continue

            # Enregistrer systématiquement dans l'historique
            price_history_repository.insert_price_point(product_url, current_price)

            if current_price < baseline_price:
                drop_percent = (baseline_price - current_price) / baseline_price * 100
                # threshold_percent NULL = comportement historique (toute baisse alerte).
                meets_threshold = threshold_percent is None or drop_percent >= threshold_percent
                if not meets_threshold:
                    continue

                # Alerte Email (respecte la préférence utilisateur)
                if profile_repository.get_email_notifications_enabled(email):
                    send_email_alert(email, product_url, current_price)

                # Alerte In-App (toujours envoyée, ce n'est pas ce que contrôle la case profil)
                message = f"Le prix du produit a baissé à {format_price(current_price)} !"
                notifications_repository.insert_notification(email, message, product_url)

                alerts_triggered.append({
                    "subscription_id": sub_id,
                    "email": email,
                    "product_url": product_url,
                    "current_price": format_price(current_price),
                    "previous_price": format_price(baseline_price)
                })
                subscriptions_repository.update_subscription_reference_price(sub_id, current_price)

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
    # En debug, le reloader Flask relance ce script dans un sous-processus : sans ce garde,
    # le scheduler démarrerait deux fois (process parent + enfant) et doublerait le rythme
    # réel des price-checks.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=run_price_check, trigger="interval", hours=2)
        scheduler.start()
    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    except (KeyboardInterrupt, SystemExit):
        pass
