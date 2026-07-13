"""Accès à la table `search_log` (historique des recherches, pour les statistiques)."""
from database import get_connection


def insert_search_log(query: str, email: str | None) -> None:
    """Enregistre une recherche effectuée (email peut être None si non connecté)."""
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO search_log (query, email) VALUES (?, ?)",
            (query, email)
        )
        connection.commit()


def get_top_searches(limit: int = 10) -> list:
    """Retourne les requêtes de recherche les plus fréquentes."""
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT query, COUNT(*) as count
            FROM search_log
            GROUP BY query
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
