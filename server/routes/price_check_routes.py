"""Endpoint /check_prices : déclenchement manuel de la vérification des abonnements."""
from flask import Blueprint, jsonify

from services import price_alert_service

price_check_bp = Blueprint("price_check", __name__)


@price_check_bp.route('/check_prices', methods=['GET'])
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
