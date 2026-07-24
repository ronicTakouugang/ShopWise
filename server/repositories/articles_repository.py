"""Accès à la table `articles` (catalogue des produits déjà vus lors d'une recherche)."""
from database import get_connection
from services import product_matching_service

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
            "SELECT product_group_id FROM articles WHERE productURL = ?", (product_url,)
        ).fetchone()
        group_id = existing["product_group_id"] if existing else None
        # Rattachement paresseux, une seule fois : un produit déjà rattaché à un groupe
        # ne doit jamais en changer à chaque rafraîchissement de prix, sous peine de
        # casser la cohérence du comparatif inter-enseigne (voir product_groups_repository).
        if group_id is None:
            group_id = product_matching_service.resolve_product_group(description)

        if existing:
            connection.execute("""
                UPDATE articles
                SET description = ?, imageURL = ?, source = ?, sourceLogo = ?,
                    rating = ?, reviewCount = ?, last_price = ?, last_seen_at = CURRENT_TIMESTAMP,
                    product_group_id = ?
                WHERE productURL = ?
            """, (description, image_url, source, source_logo, rating, review_count, last_price,
                  group_id, product_url))
        else:
            connection.execute("""
                INSERT INTO articles
                (productURL, description, imageURL, source, sourceLogo, rating, reviewCount,
                 last_price, last_seen_at, product_group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (product_url, description, image_url, source, source_logo, rating, review_count,
                  last_price, group_id))
        connection.commit()


def get_article_by_url(product_url: str):
    """Retourne l'article (source, description, last_price, ...) pour cette URL, ou None."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT source, description, last_price FROM articles WHERE productURL = ?",
            (product_url,)
        )
        return cursor.fetchone()


def get_alternatives(product_url: str) -> list:
    """
    Retourne les autres articles du même groupe de produits (rapprochement heuristique,
    voir services/product_matching_service.py) que product_url, triés par prix croissant.
    Liste vide si l'article n'est pas encore rattaché à un groupe ou n'a pas d'équivalent
    connu chez une autre enseigne.
    """
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT other.productURL AS "productURL", other.source,
                   other.sourceLogo AS "sourceLogo", other.imageURL AS "imageURL",
                   other.description, other.last_price
            FROM articles this
            JOIN articles other
                ON other.product_group_id = this.product_group_id
                AND other.productURL != this.productURL
            WHERE this.productURL = ? AND this.product_group_id IS NOT NULL
                AND other.last_price IS NOT NULL AND other.last_price < ?
            ORDER BY other.last_price ASC
        """, (product_url, MAX_PLAUSIBLE_PRICE_EUR))
        return [dict(row) for row in cursor.fetchall()]


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
