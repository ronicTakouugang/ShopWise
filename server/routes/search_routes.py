"""Endpoint /search : recherche de produits."""
import logging

from flask import Blueprint, jsonify, request, session

from services import search_service

search_bp = Blueprint("search", __name__)


@search_bp.route('/search', methods=['GET'])
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
