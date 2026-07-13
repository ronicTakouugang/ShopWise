"""Accès à la table `subscriptions` (abonnements de suivi de prix, un par produit et par utilisateur)."""
from database import get_connection


def get_subscription(email: str, product_url: str):
    """Retourne l'abonnement de cet utilisateur pour ce produit, ou None s'il n'existe pas."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT * FROM subscriptions WHERE email = ? AND product_url = ?",
            (email, product_url)
        )
        return cursor.fetchone()


def upsert_subscription(product_url: str, email: str, initial_price: float, threshold_percent: float | None) -> None:
    """
    Active le suivi de prix pour un produit précis. Si l'utilisateur suivait déjà ce
    produit, met à jour le prix de référence et le seuil au lieu de créer un doublon.
    """
    existing = get_subscription(email, product_url)
    with get_connection() as connection:
        if existing:
            connection.execute(
                "UPDATE subscriptions SET initial_price = ?, threshold_percent = ? WHERE id = ?",
                (initial_price, threshold_percent, existing["id"])
            )
        else:
            connection.execute("""
                INSERT INTO subscriptions (product_url, initial_price, email, threshold_percent)
                VALUES (?, ?, ?, ?)
            """, (product_url, initial_price, email, threshold_percent))
        connection.commit()


def delete_subscription(email: str, product_url: str) -> None:
    """Désactive le suivi de prix pour un produit précis."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM subscriptions WHERE email = ? AND product_url = ?",
            (email, product_url)
        )
        connection.commit()


def get_subscribed_urls_by_email(email: str) -> set:
    """Retourne l'ensemble des productURL suivis (alertes actives) pour cet email."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT product_url FROM subscriptions WHERE email = ?",
            (email,)
        )
        return {row["product_url"] for row in cursor.fetchall()}


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
