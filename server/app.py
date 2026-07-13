"""
Point d'entrée de l'application Flask : configuration, routes HTTP et
planification du job périodique de vérification des prix.

Toute la logique métier (recherche, alertes de prix, authentification) vit dans
services/, et tout accès à la base de données vit dans repositories/. Ce fichier
ne fait que traduire les requêtes HTTP en appels à ces couches, et les résultats
en réponses JSON.
"""
import logging
import os

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
from services import auth_service, price_alert_service, search_service
from utils import extract_price

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
        user = auth_service.register_user(email, password)
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
        user = auth_service.login_user(email, password)
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
        favorites = search_service.mark_subscriptions(favorites, email)
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
        auth_service.send_password_reset_email(email)
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
    """Recherche des produits selon un mot-clé."""
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Veuillez fournir un mot-clé via le paramètre 'query'."}), 400
    try:
        email = session.get("email")
        results = search_service.do_search_cached(query, email)
        results = search_service.mark_favorites(results, email)
        results = search_service.mark_subscriptions(results, email)
        logging.info("Recherche '%s' retournant %d résultats.", query, len(results))
        return jsonify(results)
    except Exception as e:
        logging.error("Erreur dans /search: %s", e)
        return jsonify({"error": str(e)}), 500


#########################
# Endpoints /subscribe : Alerte de baisse de prix sur UN produit précis
#########################
@app.route('/subscribe', methods=['POST'])
def subscribe():
    """
    Active le suivi de prix pour un produit précis (pas pour une recherche entière :
    c'est à l'utilisateur de choisir quel produit suivre, depuis sa carte produit).
    Corps JSON attendu : {"productURL": "...", "price": "19,99 €", "threshold_percent": 10}
    threshold_percent est optionnel : absent ou null = alerte dès la moindre baisse.
    Sinon, l'alerte n'est déclenchée que si la baisse atteint au moins ce pourcentage.
    """
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    email = session['email']

    subscribe_payload = request.get_json() or {}
    product_url = str(subscribe_payload.get("productURL", "")).strip()
    initial_price = extract_price(str(subscribe_payload.get("price", "")))
    threshold_percent = price_alert_service.parse_threshold_percent(subscribe_payload.get("threshold_percent"))

    if not product_url or initial_price == float('inf'):
        return jsonify({"error": "productURL et price (prix connu) sont requis."}), 400

    try:
        subscriptions_repository.upsert_subscription(product_url, email, initial_price, threshold_percent)
        logging.info("Alerte de prix activée pour %s sur %s (seuil: %s).", email, product_url, threshold_percent)
        return jsonify({"message": "Alerte de prix activée pour ce produit."})
    except Exception as e:
        logging.error("Erreur dans /subscribe: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/subscribe/remove', methods=['POST'])
def unsubscribe():
    """Désactive le suivi de prix pour un produit précis. Corps JSON : {"productURL": "..."}"""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    email = session['email']
    product_url = request.get_json().get("productURL") if request.get_json() else None
    if not product_url:
        return jsonify({"error": "productURL requis."}), 400
    try:
        subscriptions_repository.delete_subscription(email, product_url)
        return jsonify({"message": "Alerte de prix désactivée pour ce produit."})
    except Exception as e:
        logging.error("Erreur dans /subscribe/remove: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/check_prices', methods=['GET'])
def check_prices():
    """
    Endpoint manuel pour vérifier les prix des produits abonnés.
    Retourne un message et la liste des articles dont le prix a changé.
    """
    alerts = price_alert_service.run_price_check()
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
        scheduler.add_job(func=price_alert_service.run_price_check, trigger="interval", hours=2)
        scheduler.start()
    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    except (KeyboardInterrupt, SystemExit):
        pass
