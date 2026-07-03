import logging
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import extract_price as util_extract_price, convert_to_euro, robust_request

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_url(search_term, page=1):
    """
    Génère l'URL de recherche Walmart pour le terme donné et la page spécifiée.
    """
    base = "https://www.walmart.com/search"
    search_term = search_term.replace(" ", "+")
    return f"{base}?q={search_term}&page={page}"

def convert_price_to_euro(price_str):
    """
    Convertit un prix en Euro.
    """
    return convert_to_euro(price_str)

def scrape_walmart_record(item):
    """
    Extrait les informations d'un produit à partir d'un élément HTML.
    """
    try:
        description = "N/A"
        product_url = "N/A"
        
        # Récupération du titre/description
        title_span = item.find("span", {"data-automation-id": "product-title"})
        if title_span:
            description = title_span.get_text(strip=True)
        
        # Récupération de l'URL du produit
        a_tag = item.find("a", href=re.compile(r"/ip/"))
        if a_tag and a_tag.has_attr("href"):
            product_url = "https://www.walmart.com" + a_tag["href"]
            if description == "N/A":
                description = a_tag.get_text(strip=True)
        else:
            a_tag = item.find("a", href=True)
            if a_tag:
                product_url = "https://www.walmart.com" + a_tag["href"]
                if description == "N/A":
                    description = a_tag.get_text(strip=True)
        
        # Extraction du prix
        price_euro = "N/A"
        price_div = item.find("div", {"data-automation-id": "product-price"})
        if not price_div:
            price_div = item.select_one('div[data-testid="price-and-shipping"]')
            
        if price_div:
            text = price_div.get_text(separator=" ", strip=True)
            matches = re.findall(r"\$(\d+\.\d{2})", text)
            if matches:
                price = "$" + matches[0]
                price_euro = convert_price_to_euro(price)
            else:
                # Fallback pour d'autres formats de prix
                price_match = re.search(r"\$\d+(?:\.\d+)?", text)
                if price_match:
                    price = price_match.group()
                    price_euro = convert_price_to_euro(price)
        
        # Extraction du rating
        rating = "No Rating"
        rating_span = item.find("span", {"data-testid": "product-ratings"})
        if rating_span and rating_span.has_attr("data-value"):
            rating = rating_span["data-value"]
        else:
            rating_search = re.search(r"(\d+\.\d+)\s*out of\s*5", item.get_text(), re.IGNORECASE)
            if rating_search:
                rating = rating_search.group(1)
        
        # Extraction de l'image
        image_url = "N/A"
        image_tag = item.find("img", {"data-testid": "productTileImage"})
        if image_tag:
            image_url = image_tag.get("src") or image_tag.get("data-src") or "N/A"
        
        # Extraction des frais cachés
        hidden_fees = "N/A"
        fees_container = item.find("div", {"data-automation-id": "fulfillment-badge"})
        if fees_container:
            hidden_fees = fees_container.get_text(separator=" ", strip=True)
        
        logging.info(f"Produit extrait: {description} - {price_euro} - Rating: {rating} - Frais cachés: {hidden_fees}")
        return {
            "description": description,
            "price": price_euro,
            "rating": rating,
            "popularity": 0,  # Par défaut à 0 pour Walmart pour l'instant
            "productURL": product_url,
            "imageURL": image_url,
            "hiddenFees": hidden_fees,
            "source": "Walmart",
            "sourceLogo": "https://1000logos.net/wp-content/uploads/2017/05/Walmart-Logo.png"
        }
    
    except Exception as e:
        logging.error(f"Erreur lors de l'extraction d'un produit: {e}")
        return None

def fetch_page(search_term, page):
    """
    Récupère et parse une page donnée pour le terme de recherche.
    """
    url = get_url(search_term, page)
    logging.info(f"🌐 Récupération de la page {page}: {url}")
    
    response = robust_request(url)
    if response and response.status_code == 200:
        return page, BeautifulSoup(response.content, "html.parser")
    
    return page, None

def scrape_walmart(search_term):
    """
    Scrape les résultats Walmart pour le terme de recherche donné.
    """
    logging.info(f"🔍 Début du scraping Walmart pour: {search_term}")
    
    records = []
    pages_to_fetch = [1]  # Walmart est très sensible, on commence par une page
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_page = {
            executor.submit(fetch_page, search_term, page): page
            for page in pages_to_fetch
        }
        for future in as_completed(future_to_page):
            page, soup = future.result()
            if not soup:
                logging.warning(f"⚠ Aucune donnée récupérée pour la page {page}.")
                continue
            logging.info(f"📄 Scraping de la page {page}...")
            # Récupération de tous les produits
            product_items = soup.find_all("div", {"data-item-id": True})
            if not product_items:
                product_items = soup.select('div[data-testid="item-stack"] > div')
    
            for item in product_items:
                record = scrape_walmart_record(item)
                if record:
                    records.append(record)
    
    df = pd.DataFrame(records, columns=["description", "price", "rating", "popularity", "productURL", "imageURL", "hiddenFees", "source", "sourceLogo"])
    
    if not df.empty:
        df = df.drop_duplicates(subset=["productURL"])
        df["price_numeric"] = df["price"].apply(lambda x: util_extract_price(str(x)))
        df = df.drop(columns=["price_numeric"])
    
    # Filtrer les produits sans description ou sans URL et convertir en liste de dictionnaires
    records = [r for r in df.to_dict(orient="records") if r.get("description") != "N/A" and r.get("productURL") != "N/A"]
    
    return records
