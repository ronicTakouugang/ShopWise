"""Endpoints /subscribe : alerte de baisse de prix sur un produit précis."""
import logging

from flask import Blueprint, jsonify, request, session

from repositories import subscriptions_repository
from services import price_alert_service
from utils import extract_price

subscriptions_bp = Blueprint("subscriptions", __name__)


@subscriptions_bp.route('/subscribe', methods=['POST'])
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


@subscriptions_bp.route('/subscribe/remove', methods=['POST'])
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
