"""Accès à la table `price_history` (historique des prix observés pour un produit)."""
from database import get_connection


def get_last_price_point(product_url: str):
    """Retourne le dernier prix enregistré pour ce produit, ou None si aucun historique."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT price FROM price_history WHERE productURL = ? ORDER BY date DESC LIMIT 1",
            (product_url,)
        )
        row = cursor.fetchone()
        return row["price"] if row else None


def insert_price_point(product_url: str, price: float) -> None:
    """Ajoute un point d'historique de prix pour un produit."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO price_history (productURL, price) VALUES (?, ?)",
            (product_url, price)
        )
        connection.commit()


def get_price_history(product_url: str) -> list:
    """Retourne l'historique complet (prix, date) d'un produit, du plus ancien au plus récent."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT price, date FROM price_history WHERE productURL = ? ORDER BY date ASC",
            (product_url,)
        )
        return [dict(row) for row in cursor.fetchall()]
