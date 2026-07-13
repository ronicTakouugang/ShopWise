"""Endpoints d'authentification : inscription, connexion, déconnexion, statut, mot de passe oublié."""
import logging

from flask import Blueprint, jsonify, request, session

from services import auth_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.route('/register', methods=['POST'])
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


@auth_bp.route('/login', methods=['POST'])
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


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Déconnecte l'utilisateur en effaçant la session."""
    session.clear()
    logging.info("Utilisateur déconnecté.")
    return jsonify({"message": "Déconnexion réussie."})


@auth_bp.route('/status', methods=['GET'])
def get_status():
    """Vérifie si l'utilisateur est connecté via la session."""
    if 'email' in session:
        return jsonify({
            "isAuth": True,
            "email": session['email']
        })
    return jsonify({"isAuth": False}), 200


@auth_bp.route('/forgot_password', methods=['POST'])
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
