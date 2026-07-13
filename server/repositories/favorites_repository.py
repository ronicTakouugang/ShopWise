"""Accès à la table `favorites`."""
from database import IS_POSTGRES, get_connection

_NUMERIC_PRICE_EXPRESSION = "CAST(REPLACE(REPLACE(price, '€', ''), ',', '.') AS REAL)"
# Un prix sans valeur numérique (ex: "N/A") ne commence pas par un chiffre : ce
# CASE le place toujours après les prix valides (0 = valide, 1 = inconnu), quel
# que soit le sens du tri demandé, pour ne jamais le faire remonter en tête.
# GLOB est spécifique à SQLite ; équivalent portable en Postgres via une regex POSIX (~).
_STARTS_WITH_DIGIT = "price ~ '^[0-9]'" if IS_POSTGRES else "price GLOB '[0-9]*'"
_UNKNOWN_PRICE_LAST = f"CASE WHEN {_STARTS_WITH_DIGIT} THEN 0 ELSE 1 END ASC"

_SORT_CLAUSES = {
    # Le prix est stocké en texte avec le symbole "€" (ex: "19,99 €") : on le
    # nettoie à la volée pour trier numériquement. Idéalement ce serait une
    # colonne numérique dédiée, mais on garde le comportement existant tel quel.
    "price_asc": f"ORDER BY {_UNKNOWN_PRICE_LAST}, {_NUMERIC_PRICE_EXPRESSION} ASC",
    "price_desc": f"ORDER BY {_UNKNOWN_PRICE_LAST}, {_NUMERIC_PRICE_EXPRESSION} DESC",
    "date_added": "ORDER BY id DESC",  # approximé par l'ordre d'insertion (id)
}


def get_favorites_by_email(email: str, sort_by: str = "date_added") -> list:
    """Retourne les favoris d'un utilisateur, triés selon sort_by."""
    order_clause = _SORT_CLAUSES.get(sort_by, _SORT_CLAUSES["date_added"])
    with get_connection() as connection:
        cursor = connection.execute(
            f"SELECT * FROM favorites WHERE email = ? {order_clause}",
            (email,)
        )
        return [dict(row) for row in cursor.fetchall()]


def upsert_favorite(email: str, favorite: dict) -> None:
    """
    Ajoute ou met à jour un favori (email + productURL forment la clé unique).
    `favorite` attend les clés : description, price, imageURL, productURL,
    source, sourceLogo, rating, reviewCount.
    Vérifie l'existence puis UPDATE/INSERT plutôt qu'un "INSERT OR REPLACE" (syntaxe
    SQLite non portable vers Postgres).
    """
    product_url = favorite.get("productURL")
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT 1 FROM favorites WHERE email = ? AND productURL = ?", (email, product_url)
        ).fetchone()
        if existing:
            connection.execute("""
                UPDATE favorites
                SET description = ?, price = ?, imageURL = ?, source = ?,
                    sourceLogo = ?, rating = ?, reviewCount = ?
                WHERE email = ? AND productURL = ?
            """, (
                favorite.get("description"), favorite.get("price"), favorite.get("imageURL"),
                favorite.get("source"), favorite.get("sourceLogo"), favorite.get("rating"),
                favorite.get("reviewCount"), email, product_url,
            ))
        else:
            connection.execute("""
                INSERT INTO favorites
                (email, description, price, imageURL, productURL, source, sourceLogo, rating, reviewCount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email,
                favorite.get("description"),
                favorite.get("price"),
                favorite.get("imageURL"),
                product_url,
                favorite.get("source"),
                favorite.get("sourceLogo"),
                favorite.get("rating"),
                favorite.get("reviewCount"),
            ))
        connection.commit()


def delete_favorite(email: str, product_url: str) -> None:
    """Supprime un favori."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM favorites WHERE email = ? AND productURL = ?",
            (email, product_url)
        )
        connection.commit()


def get_favorite_urls_by_email(email: str) -> set:
    """Retourne l'ensemble des productURL en favoris pour cet email."""
    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT productURL FROM favorites WHERE email = ?",
            (email,)
        )
        return {row["productURL"] for row in cursor.fetchall()}


def count_distinct_favorited_products() -> int:
    """Nombre total de produits distincts favorisés, tous utilisateurs confondus."""
    with get_connection() as connection:
        cursor = connection.execute("SELECT COUNT(DISTINCT productURL) as count FROM favorites")
        return cursor.fetchone()["count"]
