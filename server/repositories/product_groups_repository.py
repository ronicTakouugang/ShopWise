"""Accès à la table `product_groups` (rapprochement heuristique de produits entre enseignes)."""
from database import IS_POSTGRES, get_connection

# Même garde-fou que articles_repository : exclut les prix aberrants du comparatif.
MAX_PLAUSIBLE_PRICE_EUR = 500_000


def find_candidate_groups(words: list) -> list:
    """
    Retourne les groupes existants partageant au moins un des mots significatifs donnés
    ("blocking" : borne le nombre de comparaisons de similarité à faire lors d'un
    rapprochement, au lieu de comparer contre tous les groupes connus). Un blocking par
    mot partagé - plutôt que par seul premier mot - tolère l'ordre des mots (ex: "Apple
    iPhone 15" et "iPhone 15 Pro" partagent "iphone" même si ce n'est pas leur 1er mot).
    """
    if not words:
        return []
    with get_connection() as connection:
        placeholders = ",".join(["?"] * len(words))
        cursor = connection.execute(f"""
            SELECT DISTINCT pg.id, pg.canonical_title
            FROM product_groups pg
            JOIN product_group_words w ON w.group_id = pg.id
            WHERE w.word IN ({placeholders})
        """, tuple(words))
        return [dict(row) for row in cursor.fetchall()]


def create_group(canonical_title: str, words: list) -> int:
    """Crée un nouveau groupe de produits (avec ses mots de blocking) et retourne son id."""
    with get_connection() as connection:
        if IS_POSTGRES:
            cursor = connection.execute(
                "INSERT INTO product_groups (canonical_title) VALUES (?) RETURNING id",
                (canonical_title,)
            )
            new_id = cursor.fetchone()["id"]
        else:
            cursor = connection.execute(
                "INSERT INTO product_groups (canonical_title) VALUES (?)",
                (canonical_title,)
            )
            new_id = cursor.lastrowid

        for word in words:
            connection.execute(
                "INSERT INTO product_group_words (group_id, word) VALUES (?, ?)",
                (new_id, word)
            )
        connection.commit()
        return new_id


def _find_source_for_price(connection, product_group_id: int, price: float):
    """Retourne une source vendant ce produit à ce prix exact (arbitraire en cas d'égalité)."""
    cursor = connection.execute(
        "SELECT source FROM articles WHERE product_group_id = ? AND last_price = ? LIMIT 1",
        (product_group_id, price)
    )
    row = cursor.fetchone()
    return row["source"] if row else None


def get_group_price_comparison(limit: int = 10) -> list:
    """
    Retourne, pour les produits vus chez au moins 2 enseignes différentes, l'écart de
    prix entre la source la moins chère et la plus chère, triés par économie potentielle
    décroissante. Le rapprochement étant heuristique (pas d'EAN/SKU officiel, voir
    services/product_matching_service.py), ce comparatif est best-effort : deux variantes
    proches d'un même produit peuvent être confondues ou séparées à tort.
    """
    with get_connection() as connection:
        cursor = connection.execute("""
            SELECT pg.id as group_id, pg.canonical_title,
                   MIN(a.last_price) as min_price, MAX(a.last_price) as max_price
            FROM product_groups pg
            JOIN articles a ON a.product_group_id = pg.id
            WHERE a.last_price IS NOT NULL AND a.last_price < ?
            GROUP BY pg.id, pg.canonical_title
            HAVING COUNT(DISTINCT a.source) >= 2
            ORDER BY (MAX(a.last_price) - MIN(a.last_price)) DESC
            LIMIT ?
        """, (MAX_PLAUSIBLE_PRICE_EUR, limit))
        groups = [dict(row) for row in cursor.fetchall()]

        results = []
        for group in groups:
            cheapest_source = _find_source_for_price(connection, group["group_id"], group["min_price"])
            priciest_source = _find_source_for_price(connection, group["group_id"], group["max_price"])
            results.append({
                "canonical_title": group["canonical_title"],
                "cheapest_source": cheapest_source,
                "cheapest_price": group["min_price"],
                "priciest_source": priciest_source,
                "priciest_price": group["max_price"],
                "savings": round(group["max_price"] - group["min_price"], 2),
            })
        return results
