"""Endpoints /notifications : notifications in-app de baisse de prix."""
from flask import Blueprint, jsonify, session

from repositories import notifications_repository

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route('/notifications', methods=['GET'])
def get_notifications():
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    try:
        return jsonify(notifications_repository.get_notifications_by_email(session['email']))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notifications_bp.route('/notifications/read', methods=['POST'])
def mark_notifications_read():
    """Marque toutes les notifications de l'utilisateur comme lues."""
    if 'email' not in session:
        return jsonify({"error": "Non authentifié"}), 401
    try:
        notifications_repository.mark_all_notifications_read(session['email'])
        return jsonify({"message": "Notifications marquées comme lues."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
