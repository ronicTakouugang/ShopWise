"""Authentification des utilisateurs via Firebase (Pyrebase)."""
import config

_firebase_auth = config.create_firebase_auth()


def register_user(email: str, password: str) -> dict:
    """Crée un nouvel utilisateur Firebase. Lève une exception si l'email existe déjà, etc."""
    return _firebase_auth.create_user_with_email_and_password(email, password)


def login_user(email: str, password: str) -> dict:
    """Authentifie un utilisateur Firebase. Lève une exception si les identifiants sont invalides."""
    return _firebase_auth.sign_in_with_email_and_password(email, password)


def send_password_reset_email(email: str) -> None:
    """Envoie un email de réinitialisation de mot de passe via Firebase."""
    _firebase_auth.send_password_reset_email(email)
