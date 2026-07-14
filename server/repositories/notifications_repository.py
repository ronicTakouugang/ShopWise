"""Accès à la table `in_app_notifications`."""
from database import get_connection, recent_cutoff


def get_notifications_by_email(email: str) -> list:
    """
    Retourne les notifications in-app d'un utilisateur, les plus récentes en premier.
    productURL est explicitement aliasé : Postgres met en minuscules les identifiants
    non guillemetés (productURL -> producturl) alors que SQLite préserve la casse -
    sans l'alias, le JSON renvoyé aurait une clé "producturl" en prod et "productURL"
    en local, cassant le clic "ouvrir le produit" côté client en production.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            'SELECT id, email, message, productURL AS "productURL", date, is_read '
            "FROM in_app_notifications WHERE email = ? ORDER BY date DESC",
            (email,)
        )
        return [dict(row) for row in cursor.fetchall()]


def insert_notification(email: str, message: str, product_url: str) -> None:
    """Crée une notification in-app."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO in_app_notifications (email, message, productURL)
            VALUES (?, ?, ?)
        """, (email, message, product_url))
        connection.commit()


def mark_all_notifications_read(email: str) -> None:
    """Marque toutes les notifications non lues d'un utilisateur comme lues."""
    with get_connection() as connection:
        connection.execute(
            "UPDATE in_app_notifications SET is_read = 1 WHERE email = ? AND is_read = 0",
            (email,)
        )
        connection.commit()


def count_recent_notifications(days: int = 7) -> int:
    """
    Nombre de notifications créées dans les N derniers jours, tous utilisateurs confondus.
    Le seuil est calculé côté Python (recent_cutoff) plutôt qu'avec datetime('now', ...),
    spécifique à SQLite et non portable vers Postgres.
    """
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT COUNT(*) as count FROM in_app_notifications WHERE date >= ?",
            (recent_cutoff(days),)
        )
        return cursor.fetchone()["count"]
