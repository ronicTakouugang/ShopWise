import logging
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import extract_price as util_extract_price, robust_request

logger = logging.getLogger(__name__)

DOMAIN = "https://www.auchan.fr"
# Motif de prix français : chiffres (avec espaces/espaces fines insécables comme
# séparateur de milliers), virgule décimale, symbole €.
_PRICE_PATTERN = re.compile(r"[\d\s ]+,\d{2}\s*€")


def get_url(search_term: str, page: int = 1) -> str:
    return f"{DOMAIN}/recherche?text={search_term.replace(' ', '+')}&page={page}"


def scrape_records(item) -> dict | None:
    """Extrait les informations d'un produit à partir d'une carte <article> Auchan."""
    try:
        link_el = item.select_one("a.product-thumbnail__details-wrapper")
        if not link_el or not link_el.has_attr("href"):
            return None
        product_url = DOMAIN + link_el["href"]

        # Certaines cartes affichent un petit badge (ex: icône "Surgelés"/"Sans gluten")
        # AVANT la vraie photo dans le DOM : un simple "premier <img> du lien" attrape
        # ce badge au lieu du produit. On cible donc précisément le conteneur de la
        # vraie photo (product-thumbnail__picture), qui contient aussi le vrai titre
        # via l'attribut alt de ses <source>/<img>.
        picture_el = link_el.select_one(".product-thumbnail__picture")
        title_el = picture_el.select_one("source[alt], img[alt]") if picture_el else None
        description = (title_el.get("alt") if title_el else None) or link_el.get("aria-label") or "N/A"

        image_url = "N/A"
        img = picture_el.select_one("img") if picture_el else None
        if img:
            # Les images sont chargées en lazy-load (class="lazy") : "src" ne contient
            # souvent qu'un pixel transparent de remplacement tant que le JS n'a pas
            # remplacé la source ; la vraie image est dans "data-src".
            image_url = img.get("data-src") or img.get("src") or "N/A"
            if image_url and image_url.endswith("pixel.png"):
                image_url = "N/A"

        price = "N/A"
        old_price = "N/A"
        price_container = item.select_one(".product-thumbnail__price")
        if price_container:
            # Une carte en promo affiche "ancien_prix nouveau_prix" côte à côte ;
            # sans promo, un seul prix est présent.
            matches = _PRICE_PATTERN.findall(price_container.get_text(" ", strip=True))
            if len(matches) >= 2:
                old_price = matches[0].strip()
                price = matches[1].strip()
            elif len(matches) == 1:
                price = matches[0].strip()

        return {
            "description": description,
            "price": price,
            "oldPrice": old_price,
            "productURL": product_url,
            "imageURL": image_url,
            "sourceLogo": f"{DOMAIN}/favicon.ico",
            "source": "Auchan",
            "popularity": 0,
        }
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction d'un produit Auchan : {e}")
        return None


def fetch_page(search_term: str, page: int):
    url = get_url(search_term, page)
    logger.info(f"🌐 Récupération de la page {page} : {url}")
    response = robust_request(url, accept_language="fr-FR,fr;q=0.9,en-US;q=0.7,en;q=0.5")
    if response and response.status_code == 200:
        return page, BeautifulSoup(response.content, "html.parser")
    return page, None


def scrape_auchan(search_term: str) -> list:
    """Scrape les résultats Auchan pour le terme de recherche donné (2 pages, en parallèle)."""
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
            items = soup.select("article.product-thumbnail")
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
