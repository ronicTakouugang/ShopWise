import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from utils import extract_price as util_extract_price, robust_request

logger = logging.getLogger(__name__)

DOMAIN = "https://www.materiel.net"


def get_url(search_term: str, page: int = 1) -> str:
    query = urllib.parse.quote(search_term.strip())
    if page <= 1:
        return f"{DOMAIN}/recherche/{query}/"
    return f"{DOMAIN}/recherche/{query}/page{page}/"


def _parse_price(price_el) -> str:
    """
    Le prix est affiché en deux morceaux : le texte direct de l'élément ("99€")
    et les centimes dans un <sup> ("95"), sans virgule ni espace entre les deux
    (rendu visuel "99€95" pour 99,95€).
    """
    if not price_el:
        return "N/A"
    main_text = price_el.find(string=True, recursive=False)
    if not main_text or not main_text.strip():
        return "N/A"
    euros = main_text.strip().replace("€", "").strip()
    if not euros:
        return "N/A"
    sup = price_el.select_one("sup")
    cents = sup.get_text(strip=True) if sup else "00"
    return f"{euros},{cents} €"


def scrape_records(item) -> dict | None:
    """Extrait les informations d'un produit à partir d'une carte <li class="c-products-list__item">."""
    try:
        link_el = item.select_one("a.c-product__link")
        if not link_el or not link_el.has_attr("href"):
            return None
        product_url = link_el["href"]

        title_el = item.select_one(".c-product__title")
        description = title_el.get_text(strip=True) if title_el else (link_el.get("title") or "N/A")

        image_url = "N/A"
        img = item.select_one(".c-product__thumb img")
        if img:
            image_url = img.get("src") or img.get("data-src") or "N/A"

        # En promo : prix courant marqué "--promo", prix barré marqué "cut-price".
        # Sans promo : un seul prix, sans modificateur.
        promo_price_el = item.select_one(".o-product__price--promo")
        cut_price_el = item.select_one(".o-product__cut-price")
        if promo_price_el:
            price = _parse_price(promo_price_el)
            old_price = _parse_price(cut_price_el)
        else:
            price = _parse_price(item.select_one(".o-product__price"))
            old_price = "N/A"

        return {
            "description": description,
            "price": price,
            "oldPrice": old_price,
            "productURL": product_url,
            "imageURL": image_url,
            "sourceLogo": f"{DOMAIN}/favicon.ico",
            "source": "Materiel.net",
            "popularity": 0,
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction d'un produit Materiel.net : {e}")
        return None


def fetch_page(search_term: str, page: int):
    url = get_url(search_term, page)
    logger.info(f"🌐 Récupération de la page {page} : {url}")
    response = robust_request(url, accept_language="fr-FR,fr;q=0.9,en-US;q=0.7,en;q=0.5")
    if response and response.status_code == 200:
        return page, BeautifulSoup(response.content, "html.parser")
    return page, None


def scrape_materielnet(search_term: str) -> list:
    """Scrape les résultats Materiel.net pour le terme de recherche donné (2 pages, en parallèle)."""
    records = []
    pages_to_fetch = [1, 2]

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(fetch_page, search_term, page): page
            for page in pages_to_fetch
        }
        for future in as_completed(futures):
            page, soup = future.result()
            if not soup:
                logger.warning(f"Aucune donnée récupérée pour la page {page}.")
                continue
            items = soup.select(".c-products-list__item")
            if not items:
                logger.warning(f"Aucun produit trouvé sur la page {page}.")
                continue
            for item in items:
                record = scrape_records(item)
                if record:
                    records.append(record)

    seen = set()
    unique_records = []
    for record in records:
        if record["productURL"] not in seen:
            seen.add(record["productURL"])
            unique_records.append(record)

    unique_records = [
        r for r in unique_records
        if r.get("description") != "N/A" and r.get("productURL")
    ]
    unique_records.sort(key=lambda r: util_extract_price(str(r.get("price", ""))))
    return unique_records
