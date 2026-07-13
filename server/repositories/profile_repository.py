"""Accès à la table `user_profile`."""
from database import get_connection


def get_profile_by_email(email: str):
    """Retourne le profil utilisateur (dict-like), ou None si inexistant."""
    with get_connection() as connection:
        cursor = connection.execute("SELECT * FROM user_profile WHERE email = ?", (email,))
        return cursor.fetchone()


def create_default_profile(email: str, display_name: str) -> None:
    """Crée un profil par défaut (notifications activées) pour un nouvel utilisateur."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO user_profile (email, display_name) VALUES (?, ?)",
            (email, display_name)
        )
        connection.commit()


def upsert_profile(email: str, display_name: str, notifications_enabled: bool) -> None:
    """
    Crée ou met à jour le profil utilisateur. Vérifie l'existence puis UPDATE/INSERT
    plutôt qu'un "INSERT OR REPLACE" (syntaxe SQLite non portable vers Postgres).
    """
    with get_connection() as connection:
        existing = connection.execute("SELECT 1 FROM user_profile WHERE email = ?", (email,)).fetchone()
        if existing:
            connection.execute(
                "UPDATE user_profile SET display_name = ?, notifications_enabled = ? WHERE email = ?",
                (display_name, notifications_enabled, email)
            )
        else:
            connection.execute(
                "INSERT INTO user_profile (email, display_name, notifications_enabled) VALUES (?, ?, ?)",
                (email, display_name, notifications_enabled)
            )
        connection.commit()


def get_email_notifications_enabled(email: str) -> bool:
    """
    Indique si l'utilisateur souhaite recevoir des emails d'alerte de baisse de prix.
    Retourne True par défaut si aucun profil n'est trouvé (comportement historique).
    """
    profile = get_profile_by_email(email)
    if profile is None:
        return True
    return bool(profile["notifications_enabled"])
