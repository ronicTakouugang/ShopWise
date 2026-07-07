import logging
from utils import extract_price as util_extract_price, convert_to_euro, robust_request

# Configuration du logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

SEARCH_API_URL = "https://glotelho.cm/api/v2/products/search"

def fetch_page(search_term, page, limit=40):
    """Appelle directement l'API de recherche interne (Typesense) de Glotelho."""
    payload = {
        "searchKey": search_term,
        "searchEngine": "TYPESENSE",
        "limit": str(limit),
        "page": page,
    }
    logging.info(f"🌐 Récupération page {page} via l'API pour '{search_term}'")

    response = robust_request(SEARCH_API_URL, method="POST", json=payload)
    if response and response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            logging.error("Réponse non-JSON reçue de l'API")
            return None

    return None

def scrape_glotelho(search_term, max_pages=3):
    """Récupère les produits depuis l'API de recherche Glotelho, en évitant les doublons."""
    records = []
    seen = set()

    for page in range(1, max_pages + 1):
        data = fetch_page(search_term, page)
        if not data or not data.get("success"):
            logging.warning(f"⚠️ Échec de la récupération des données pour la page {page}")
            continue

        hits = data.get("data", {}).get("hits", [])
        if not hits:
            logging.info(f"ℹ️ Aucun résultat trouvé sur la page {page}")
            break  # plus de résultats, inutile de continuer à paginer

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

        # Stop pagination early if we've already retrieved everything available
        found = data.get("data", {}).get("found", 0)
        if page * 40 >= found:
            break

    records = sorted(records, key=lambda x: util_extract_price(x["price"]))
    return records

