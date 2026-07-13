import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import extract_price as util_extract_price, convert_to_euro, robust_request

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SEARCH_API_URL = "https://glotelho.cm/api/v2/products/search"
DEFAULT_PAGE_LIMIT = 40


def fetch_page(search_term, page, limit=DEFAULT_PAGE_LIMIT):
    """Appelle directement l'API de recherche interne (Typesense) de Glotelho."""
    payload = {
        "searchKey": search_term,
        "searchEngine": "TYPESENSE",
        "limit": str(limit),
        "page": page,
    }
    logging.info(f"🌐 Récupération page {page} via l'API pour '{search_term}'")

    response = robust_request(
        SEARCH_API_URL, method="POST", json=payload,
        accept_language="fr-FR,fr;q=0.9,en-US;q=0.7,en;q=0.5"
    )
    if response and response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            logging.error("Réponse non-JSON reçue de l'API")
            return None

    return None


def parse_hits(hits, seen):
    """
    Transforme une liste de hits bruts de l'API en records homogènes pour le reste
    du pipeline. `seen` est un set partagé entre pages pour éviter les doublons
    (un même produit peut apparaître sur plusieurs pages si les résultats bougent
    entre deux appels).
    """
    records = []
    for hit in hits:
        try:
            doc = hit.get("document", {})

            title = doc.get("name", "N/A")
            product_url = doc.get("url", "N/A")
            image_url = doc.get("image_url") or doc.get("thumbnail_url") or "N/A"

            # Prix : priorité XAF, fallback XOF (même valeur pour le Cameroun)
            price_info = doc.get("price", {}).get("XAF") or doc.get("price", {}).get("XOF") or {}
            price_raw = price_info.get("default_formated", "N/A")
            old_price_raw = price_info.get("default_original_formated", "N/A")

            # Popularité (vue sur certains documents d'API)
            popularity = doc.get("popularity", 0) or doc.get("views_count", 0)

            price = convert_to_euro(price_raw) if price_raw != "N/A" else "N/A"
            old_price = convert_to_euro(old_price_raw) if old_price_raw != "N/A" else "N/A"

            # Sécurité supplémentaire : s'il reste "FCFA" ou "CFA" après conversion (erreur potentielle)
            if isinstance(price, str) and ("FCFA" in price or "CFA" in price):
                price = convert_to_euro(price)
            if isinstance(old_price, str) and ("FCFA" in old_price or "CFA" in old_price):
                old_price = convert_to_euro(old_price)

            key = product_url if product_url != "N/A" else title

            if key not in seen:
                seen.add(key)
                records.append({
                    "description": title,
                    "price": price,
                    "oldPrice": old_price,
                    "popularity": popularity,
                    "productURL": product_url,
                    "imageURL": image_url,
                    "sourceLogo": "https://glotelho.cm/media/favicon/default/favicon-glotelho.png",
                    "source": "Glotehlo",
                })
        except Exception as e:
            logging.error(f"Erreur d'extraction : {e}")
    return records


def scrape_glotelho(search_term, max_pages=3, limit=DEFAULT_PAGE_LIMIT):
    """
    Récupère les produits depuis l'API de recherche Glotelho, en évitant les doublons.

    La page 1 est récupérée seule car elle indique le nombre total de résultats
    ("found"), ce qui permet de savoir combien de pages suivantes valent vraiment
    la peine d'être demandées. Ces pages suivantes (s'il y en a) sont ensuite
    récupérées en parallèle plutôt que séquentiellement, ce qui réduit nettement
    le temps total d'une recherche à plusieurs pages.
    """
    first_page = fetch_page(search_term, 1, limit)
    if not first_page or not first_page.get("success"):
        logging.warning("⚠️ Échec de la récupération des données pour la page 1")
        return []

    seen = set()
    records = parse_hits(first_page.get("data", {}).get("hits", []), seen)

    found = first_page.get("data", {}).get("found", 0)
    pages_needed = min(max_pages, math.ceil(found / limit)) if found else 1

    if pages_needed > 1:
        remaining_pages = list(range(2, pages_needed + 1))
        pages_data = {}
        with ThreadPoolExecutor(max_workers=len(remaining_pages)) as executor:
            futures = {
                executor.submit(fetch_page, search_term, page, limit): page
                for page in remaining_pages
            }
            for future in as_completed(futures):
                page = futures[future]
                data = future.result()
                if data and data.get("success"):
                    pages_data[page] = data
                else:
                    logging.warning(f"⚠️ Échec de la récupération des données pour la page {page}")

        # Traitées dans l'ordre des pages pour un résultat stable et reproductible,
        # même si les requêtes parallèles reviennent dans le désordre.
        for page in sorted(pages_data.keys()):
            hits = pages_data[page].get("data", {}).get("hits", [])
            records.extend(parse_hits(hits, seen))

    records = sorted(records, key=lambda x: util_extract_price(x["price"]))
    return records
