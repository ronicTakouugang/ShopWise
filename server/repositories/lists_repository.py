"""Accès aux tables `favorite_lists` et `favorite_list_items` (listes personnalisées)."""
from database import IS_POSTGRES, get_connection


def get_lists_by_email(email: str) -> list:
    """Retourne les listes de favoris personnalisées d'un utilisateur."""
    with get_connection() as connection:
        cursor = connection.execute("SELECT * FROM favorite_lists WHERE email = ?", (email,))
        return [dict(row) for row in cursor.fetchall()]


def create_list(email: str, name: str) -> int:
    """
    Crée une nouvelle liste de favoris personnalisée et retourne son id.
    cursor.lastrowid n'existe pas sur Postgres (psycopg2) : on utilise RETURNING id
    à la place, non supporté par ce projet sur SQLite (Python bundle des versions
    de SQLite antérieures à 3.35 sur certains systèmes), d'où la branche explicite.
    """
    with get_connection() as connection:
        if IS_POSTGRES:
            cursor = connection.execute(
                "INSERT INTO favorite_lists (email, name) VALUES (?, ?) RETURNING id",
                (email, name)
            )
            connection.commit()
            return cursor.fetchone()["id"]

        cursor = connection.execute(
            "INSERT INTO favorite_lists (email, name) VALUES (?, ?)",
            (email, name)
        )
        connection.commit()
        return cursor.lastrowid


def list_belongs_to_email(list_id: int, email: str) -> bool:
    """Vérifie qu'une liste appartient bien à cet utilisateur (contrôle d'accès)."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT 1 FROM favorite_lists WHERE id = ? AND email = ?",
            (list_id, email)
        )
        return cursor.fetchone() is not None


def add_item_to_list(list_id: int, product_url: str) -> None:
    """Ajoute un produit à une liste de favoris personnalisée."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO favorite_list_items (list_id, productURL) VALUES (?, ?)",
            (list_id, product_url)
        )
        connection.commit()
