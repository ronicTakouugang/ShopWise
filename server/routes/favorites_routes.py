"""Endpoints /favorites : liste, ajout et suppression des favoris."""
import logging

from flask import Blueprint, jsonify, request, session

from repositories import favorites_repository, price_history_repository
from services import search_service
from utils import extract_price

favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route('/favorites', methods=['GET'])
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


@favorites_bp.route('/favorites', methods=['POST'])
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


@favorites_bp.route('/favorites/remove', methods=['POST'])
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
