"""
Endpoints /analytics/summary, /price_history (+ variantes groupées) et
/articles/alternatives : statistiques, historique de prix et rapprochement inter-enseigne.
"""
import logging

from flask import Blueprint, jsonify, request

from repositories import (
    articles_repository,
    favorites_repository,
    notifications_repository,
    price_history_repository,
    product_groups_repository,
    search_log_repository,
    subscriptions_repository,
)

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route('/price_history', methods=['GET'])
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


@analytics_bp.route('/price_history/group', methods=['GET'])
def get_group_price_history():
    """
    Historique de prix agrégé pour tous les articles du même groupe de produits (voir
    services/product_matching_service.py) que productURL. Équivaut à /price_history si
    l'article n'est rapproché avec aucun autre.
    """
    product_url = request.args.get('productURL')
    if not product_url:
        return jsonify({"error": "productURL requis"}), 400

    try:
        return jsonify(price_history_repository.get_group_price_history(product_url))
    except Exception as e:
        logging.error("Erreur lors de la récupération de l'historique groupé: %s", e)
        return jsonify({"error": str(e)}), 500


@analytics_bp.route('/articles/alternatives', methods=['GET'])
def get_article_alternatives():
    """Autres enseignes vendant le même produit (rapprochement heuristique) que productURL."""
    product_url = request.args.get('productURL')
    if not product_url:
        return jsonify({"error": "productURL requis"}), 400

    try:
        return jsonify(articles_repository.get_alternatives(product_url))
    except Exception as e:
        logging.error("Erreur lors de la récupération des alternatives: %s", e)
        return jsonify({"error": str(e)}), 500


@analytics_bp.route('/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """
    Statistiques globales : recherches les plus fréquentes, comparatif agrégé par source
    (prix moyen/min/max), baisses de prix récentes, nombre de produits suivis, et les
    meilleures économies inter-enseignes (cross_retailer_deals). Ce dernier repose sur un
    rapprochement heuristique par similarité textuelle (pas de SKU/EAN officiel, voir
    services/product_matching_service.py) : best-effort, pas un identifiant produit garanti.
    """
    try:
        return jsonify({
            "top_searches": search_log_repository.get_top_searches(limit=10),
            "source_stats": articles_repository.get_price_stats_by_source(),
            "recent_price_drops": notifications_repository.count_recent_notifications(days=7),
            "tracked_subscriptions": subscriptions_repository.count_subscriptions(),
            "tracked_favorites": favorites_repository.count_distinct_favorited_products(),
            "cross_retailer_deals": product_groups_repository.get_group_price_comparison(),
        })
    except Exception as e:
        logging.error("Erreur lors du calcul des statistiques analytics: %s", e)
        return jsonify({"error": str(e)}), 500
