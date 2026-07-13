"""Accès à la table `articles` (catalogue des produits déjà vus lors d'une recherche)."""
from database import get_connection

# Aucun produit de ce catalogue ne vaut légitimement plus que ça : filet de
# sécurité contre un bug de parsing de prix dans un scraper (cf. bug historique
# de conversion FCFA -> prix ~656x trop élevé).
MAX_PLAUSIBLE_PRICE_EUR = 500_000


def upsert_article(product_url: str, description: str, image_url: str, source: str,
                    source_logo: str, rating: str, review_count: str, last_price: float) -> None:
    """
    Crée ou met à jour un article du catalogue (productURL est la clé unique).
    Vérifie l'existence puis UPDATE/INSERT plutôt qu'un "INSERT OR REPLACE" (syntaxe
    SQLite non portable vers Postgres).
    """
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT 1 FROM articles WHERE productURL = ?", (product_url,)
        ).fetchone()
        if existing:
            connection.execute("""
                UPDATE articles
                SET description = ?, imageURL = ?, source = ?, sourceLogo = ?,
                    rating = ?, reviewCount = ?, last_price = ?, last_seen_at = CURRENT_TIMESTAMP
                WHERE productURL = ?
            """, (description, image_url, source, source_logo, rating, review_count, last_price, product_url))
        else:
            connection.execute("""
                INSERT INTO articles
                (productURL, description, imageURL, source, sourceLogo, rating, reviewCount, last_price, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (product_url, description, image_url, source, source_logo, rating, review_count, last_price))
        connection.commit()


def get_article_by_url(product_url: str):
    """Retourne l'article (source, description, last_price, ...) pour cette URL, ou None."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT source, description, last_price FROM articles WHERE productURL = ?",
            (product_url,)
        )
        return cursor.fetchone()


def get_price_stats_by_source() -> list:
    """
    Retourne, pour chaque source (Amazon, Glotehlo, ...), le nombre de produits suivis
    et le prix moyen/min/max. Exclut les prix invraisemblables (voir MAX_PLAUSIBLE_PRICE_EUR).
    """
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT source,
                   COUNT(*) as product_count,
                   AVG(last_price) as avg_price,
                   MIN(last_price) as min_price,
                   MAX(last_price) as max_price
            FROM articles
            WHERE last_price IS NOT NULL AND last_price < ?
            GROUP BY source
        """, (MAX_PLAUSIBLE_PRICE_EUR,))
        return [dict(row) for row in cursor.fetchall()]
