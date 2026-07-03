import logging
import math
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from curl_cffi import requests as curl_requests
from utils import get_robust_headers

logger = logging.getLogger(__name__)

API_URL = "https://www.e.leclerc/api/rest/live-api/product-search"
PRODUCT_URL_TEMPLATE = "https://www.e.leclerc/fp/{slug}-{sku}"
DOMAIN = "https://www.e.leclerc"

# Session par thread (curl_cffi/libcurl n'est pas thread-safe sur une session partagée)
_thread_local = threading.local()


def _get_session():
    if not hasattr(_thread_local, "session"):
        _thread_local.session = curl_requests.Session()
    return _thread_local.session


def _api_headers():
    headers = get_robust_headers()
    headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.e.leclerc",
        "Referer": "https://www.e.leclerc/recherche",
    })
    return headers


def fetch_search_page(search_term, page=1, size=32, impersonate="chrome120", timeout=10, max_retries=3):
    """
    Appelle directement l'API produit-search de Leclerc (celle utilisée par leur front Angular).
    Retourne le JSON parsé, ou None en cas d'échec définitif.
    """
    payload = {
        "text": search_term,
        "filters": {"oaf-sign-code": {"value": ["0100", "0000"]}},
        "language": "fr-FR",
        "page": page,
        "size": size,
        "pertimmContexts": [],
    }

    last_status = None
    for attempt in range(max_retries):
        try:
            # Petit pacing pour rester discret, sans plomber la vitesse
            time.sleep(random.uniform(0.15, 0.4))

            session = _get_session()
            response = session.post(
                API_URL,
                json=payload,
                headers=_api_headers(),
                impersonate=impersonate,
                timeout=timeout,
            )

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as e:
                    logger.error(f"❌ Réponse non-JSON pour '{search_term}' page {page}: {e}")
                    last_status = "invalid_json"
                    continue

            last_status = response.status_code
            logger.warning(f"⚠️ Statut {response.status_code} pour '{search_term}' page {page}, tentative {attempt+1}/{max_retries}")

        except Exception as e:
            last_status = str(e)
            logger.error(f"❌ Exception API pour '{search_term}' page {page} : {e}")

    logger.error(f"❌ Échec définitif API pour '{search_term}' page {page} (dernier statut: {last_status})")
    return None


def _extract_attribute(attributes, code):
    for attr in attributes or []:
        if attr.get("code") == code:
            return attr.get("value")
    return None


def parse_item(item):
    """Transforme un item brut de l'API en record homogène pour le reste du pipeline."""
    try:
        label = item.get("label", "N/A")
        slug = item.get("slug", "")
        sku = item.get("sku") or item.get("id", "")

        variants = item.get("variants") or []
        variant = variants[0] if variants else {}
        attributes = variant.get("attributes") or []

        # Marque : d'abord dans les attributs de variante, sinon dans attributeGroups
        brand_val = _extract_attribute(attributes, "marque")
        if not brand_val:
            for group in item.get("attributeGroups") or []:
                brand_val = _extract_attribute(group.get("attributes"), "marque")
                if brand_val:
                    break
        brand = brand_val.get("label") if isinstance(brand_val, dict) else (brand_val or "N/A")

        # Image : attribut image1
        image_val = _extract_attribute(attributes, "image1")
        image_url = image_val.get("url") if isinstance(image_val, dict) else "N/A"

        # Offre par défaut (la moins chère / celle marquée isDefault, sinon la première)
        offers = variant.get("offers") or []
        offer = next((o for o in offers if o.get("isDefault")), offers[0] if offers else None)

        price, old_price, seller = "N/A", "N/A", "E.Leclerc"
        if offer:
            seller = (offer.get("shop") or {}).get("label", "E.Leclerc")
            base_price = offer.get("basePrice") or {}
            current_cents = (base_price.get("price") or {}).get("price")
            discount = base_price.get("discountPrice")

            if discount:
                # Il y a une promo : le prix "barré" est le prix normal, le prix affiché est la promo
                old_cents = current_cents
                promo_cents = (discount.get("price") or {}).get("price")
                if old_cents is not None:
                    old_price = f"{old_cents / 100:.2f} €"
                if promo_cents is not None:
                    price = f"{promo_cents / 100:.2f} €"
            elif current_cents is not None:
                price = f"{current_cents / 100:.2f} €"

        product_url = PRODUCT_URL_TEMPLATE.format(slug=slug, sku=sku) if slug and sku else DOMAIN

        return {
            "description": f"{label} - {brand}" if brand and brand != "N/A" else label,
            "price": price,
            "oldPrice": old_price,
            "productURL": product_url,
            "imageURL": image_url or "N/A",
            "seller": seller,
            "sourceLogo": "https://www.e.leclerc/favicon.ico",
            "source": "E.Leclerc",
            "popularity": 0,
            "key": sku or product_url,
        }
    except Exception as e:
        logger.error(f"Erreur d'extraction (item API) : {e}")
        return None


def scrape_leclerc(search_term, max_pages=1, size=32, parallel_pages=True, max_workers=4):
    """
    Scrape les produits Leclerc via l'API JSON interne (rapide et fiable, pas de HTML/JS).

    max_pages : nombre de pages à récupérer. Si None, récupère automatiquement toutes les pages
    disponibles d'après le champ `total` renvoyé par l'API (utile pour une récupération exhaustive).
    """
    first_page = fetch_search_page(search_term, page=1, size=size)
    if not first_page:
        return []

    total_items = first_page.get("total", 0)
    total_pages = math.ceil(total_items / size) if size else 1

    if max_pages is not None:
        total_pages = min(total_pages, max_pages)

    pages_data = {1: first_page}

    if total_pages > 1:
        remaining_pages = list(range(2, total_pages + 1))
        if parallel_pages:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(remaining_pages))) as executor:
                futures = {
                    executor.submit(fetch_search_page, search_term, page, size): page
                    for page in remaining_pages
                }
                for future in as_completed(futures):
                    page = futures[future]
                    result = future.result()
                    if result:
                        pages_data[page] = result
        else:
            for page in remaining_pages:
                result = fetch_search_page(search_term, page, size)
                if result:
                    pages_data[page] = result

    records = []
    seen = set()
    for page in sorted(pages_data.keys()):
        items = pages_data[page].get("items") or []
        for item in items:
            record = parse_item(item)
            if record is None:
                continue
            key = record.pop("key")
            if key not in seen:
                seen.add(key)
                records.append(record)

    def _price_sort_key(rec):
        if rec["price"] == "N/A":
            return float("inf")
        try:
            return float(rec["price"].replace("€", "").replace(",", ".").strip())
        except ValueError:
            return float("inf")

    records.sort(key=_price_sort_key)
    return records


def scrape_multiple_terms(search_terms, max_pages=1, max_workers=3):
    """Scrape plusieurs mots-clés en parallèle. Retourne un dict {search_term: records}."""
    results = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(search_terms))) as executor:
        futures = {
            executor.submit(scrape_leclerc, term, max_pages): term
            for term in search_terms
        }
        for future in as_completed(futures):
            term = futures[future]
            try:
                results[term] = future.result()
            except Exception as e:
                logger.error(f"Erreur lors du scraping de '{term}' : {e}")
                results[term] = []

    return results