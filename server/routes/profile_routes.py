"""Endpoints /profile : consultation et mise à jour du profil utilisateur."""
import logging

from flask import Blueprint, jsonify, request, session

from repositories import profile_repository

profile_bp = Blueprint("profile", __name__)


@profile_bp.route('/profile', methods=['GET'])
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


@profile_bp.route('/profile', methods=['POST'])
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
