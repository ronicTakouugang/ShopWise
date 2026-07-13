"""Accès à la table `subscriptions` (abonnements de suivi de prix)."""
from database import get_connection


def insert_subscription(product_url: str, email: str, initial_price: float, threshold_percent: float | None) -> None:
    """Crée un abonnement de suivi de prix pour un produit."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO subscriptions (product_url, initial_price, email, threshold_percent)
            VALUES (?, ?, ?, ?)
        """, (product_url, initial_price, email, threshold_percent))
        connection.commit()


def get_all_subscriptions() -> list:
    """Retourne tous les abonnements actifs (utilisé par la vérification périodique des prix)."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT id, product_url, initial_price, email, threshold_percent FROM subscriptions"
        )
        return cursor.fetchall()


def update_subscription_reference_price(subscription_id: int, new_price: float) -> None:
    """Met à jour le prix de référence d'un abonnement après une alerte déclenchée."""
    with get_connection() as connection:
        connection.execute(
            "UPDATE subscriptions SET initial_price = ? WHERE id = ?",
            (new_price, subscription_id)
        )
        connection.commit()


def count_subscriptions() -> int:
    """Nombre total d'abonnements actifs."""
    with get_connection() as connection:
        cursor = connection.execute("SELECT COUNT(*) as count FROM subscriptions")
        return cursor.fetchone()["count"]
