#!/usr/bin/env python3
import logging
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import extract_price as util_extract_price, convert_to_euro, robust_request

# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Fonctions Utilitaires
# -----------------------------------------------------------------------------
def get_url(search_term, page=1):
    """
    Génère l'URL de recherche Amazon pour le mot-clé donné et la page spécifiée.
    """
    base = "https://www.amazon.com/s"
    search_term = search_term.replace(" ", "+")
    return f"{base}?k={search_term}&page={page}"

def convert_price_to_euro(price_str):
    """
    Convertit un montant exprimé en devise (€, $, £) en Euro.
    """
    return convert_to_euro(price_str)

def scrape_records(item):
    """
    Extrait les informations d'un produit à partir d'un élément HTML.
    """
    try:
        # Description et URL
        description = "N/A"
        product_url = "N/A"
        title_container = item.select_one("div[data-cy='title-recipe']")
        if title_container:
            h2 = title_container.select_one("h2")
            if h2:
                description = h2.get_text(strip=True)
            else:
                a_tag = title_container.find("a")
                if a_tag:
                    description = a_tag.get_text(strip=True)
            a_tag = title_container.find("a")
            if a_tag and a_tag.has_attr("href"):
                product_url = "https://amazon.com" + a_tag["href"]
        # Fallback en cas d'absence du container principal
        if product_url == "N/A":
            a_tag = item.find("a", href=re.compile("/dp/"))
            if a_tag and a_tag.has_attr("href"):
                product_url = "https://amazon.com" + a_tag["href"]
            if description == "N/A":
                alt_title = item.select_one("h2.a-size-base-plus")
                if alt_title:
                    description = alt_title.get_text(strip=True)
        
        # Prix principal
        price_euro = "N/A"
        price = "N/A"
        price_container = item.select_one("div[data-cy='price-recipe'] span.a-offscreen")
        if not price_container:
            price_container = item.select_one("span.a-price span.a-offscreen")
        
        if price_container:
            price = price_container.get_text(strip=True)
            price_euro = convert_price_to_euro(price)

        # Rating
        rating_container = item.select_one("span.a-icon-alt")
        rating = rating_container.get_text(strip=True) if rating_container else "No Rating"
        
        # Extraire le nombre de ventes ou d'avis (pour la pertinence)
        popularity = 0
        popularity_container = item.select_one("span.a-size-base.s-underline-text")
        if not popularity_container:
            popularity_container = item.select_one("span.a-size-base") # Autre sélecteur possible
            
        if popularity_container:
            pop_text = popularity_container.get_text(strip=True).replace("(", "").replace(")", "").replace(".", "").replace(",", "").replace("\u00a0", "")
            # On prend seulement les chiffres
            pop_digits = "".join(filter(str.isdigit, pop_text))
            if pop_digits:
                popularity = int(pop_digits)

        # Image URL
        image_url = "N/A"
        image_container = item.find("img", class_="s-image")
        if image_container:
            # Liste des attributs à tester par ordre de priorité
            img_attrs = ["data-a-dynamic-image", "srcset", "data-src", "src"]
            
            for attr in img_attrs:
                val = image_container.get(attr)
                if not val:
                    continue
                
                # Cas spécial : data-a-dynamic-image est un JSON
                if attr == "data-a-dynamic-image" and val.startswith("{"):
                    try:
                        import json
                        img_dict = json.loads(val)
                        if img_dict:
                            # On prend l'image avec la plus grande résolution
                            sorted_imgs = sorted(img_dict.items(), key=lambda x: x[1][0] * x[1][1], reverse=True)
                            candidate = sorted_imgs[0][0]
                            if candidate and "grey-pixel" not in candidate and "sprite" not in candidate and "transparent-pixel" not in candidate and "01rrzVoKd5L.svg" not in candidate:
                                image_url = candidate
                                break
                    except:
                        continue
                
                # Cas spécial : srcset est une liste d'URLs
                elif attr == "srcset":
                    candidates = [c.strip().split(" ")[0] for c in val.split(",")]
                    # On prend la dernière qui n'est pas un placeholder
                    for candidate in reversed(candidates):
                        if candidate and "grey-pixel" not in candidate and "sprite" not in candidate and "transparent-pixel" not in candidate and "01rrzVoKd5L.svg" not in candidate:
                            image_url = candidate
                            break
                    if image_url != "N/A":
                        break
                
                # Cas standard : src ou data-src
                else:
                    if val and "grey-pixel" not in val and "sprite" not in val and "transparent-pixel" not in val and "01rrzVoKd5L.svg" not in val:
                        image_url = val
                        break
        
        # Fallback ultime : si on a toujours rien ou un placeholder, on tente de trouver n'importe quelle image dans l'item
        if image_url == "N/A" or "grey-pixel" in image_url or "transparent-pixel" in image_url or "01rrzVoKd5L.svg" in image_url:
            all_imgs = item.find_all("img")
            for img in all_imgs:
                # Priorité aux images qui ne sont pas des logos de source ou des icônes
                src = img.get("data-src") or img.get("src") or img.get("srcset")
                if src:
                    if "," in src and "http" in src:
                        src = src.split(",")[0].split(" ")[0]
                    
                    if "http" in src and "grey-pixel" not in src and "sprite" not in src and "transparent-pixel" not in src and "01rrzVoKd5L.svg" not in src and "logo" not in src.lower():
                        image_url = src
                        break

        # Frais cachés
        hidden_fees_container = item.select_one("div[data-cy='delivery-recipe'] span.a-color-base")
        if hidden_fees_container:
            hidden_fees_text = hidden_fees_container.get_text(strip=True)
            hidden_fees_text = hidden_fees_text.replace("Livraison à", "").strip()
            hidden_fees_euro = convert_price_to_euro(hidden_fees_text)
        else:
            hidden_fees_euro = "N/A"

        logger.info(f"Produit extrait : {description} - {price} -> {price_euro} | Frais caches : {hidden_fees_euro}")
        return {
            "description": description,
            "price": price_euro,
            "rating": rating,
            "popularity": popularity,
            "productURL": product_url,
            "imageURL": image_url,
            "hiddenFees": hidden_fees_euro,
            "sourceLogo": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Amazon_logo.svg/1024px-Amazon_logo.svg.png",
            "source": "Amazon"
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction d'un produit : {e}")
        return None

def fetch_page(search_term, page):
    """
    Récupère et parse une page donnée pour un terme de recherche.
    """
    url = get_url(search_term, page)
    logger.info(f"🌐 Récupération de la page {page} : {url}")
    
    response = robust_request(url)
    if response and response.status_code == 200:
        return page, BeautifulSoup(response.content, "html.parser")
    
    return page, None

def scrape_amazon(search_term):
    """
    Scrape les resultats Amazon pour le terme de recherche donne.
    """
    logger.info(f"Demarrage du scraping pour : {search_term}")
    
    records = []
    pages_to_fetch = list(range(1, 3))  # Limite a 2 pages pour plus de rapidite et discretion

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_page = {
            executor.submit(fetch_page, search_term, page): page
            for page in pages_to_fetch
        }
        for future in as_completed(future_to_page):
            page, soup = future.result()
            if not soup:
                logger.warning(f"Aucune donnee recuperee pour la page {page}.")
                continue
            logger.info(f"Scraping de la page {page}...")
            results = soup.find_all("div", {"data-component-type": "s-search-result"})
            if not results:
                logger.warning(f"Aucune donnee trouvee sur la page {page}.")
                continue
            for item in results:
                record = scrape_records(item)
                if record:
                    records.append(record)
    
    df = pd.DataFrame(records, columns=["description", "price", "rating", "popularity", "productURL", "imageURL", "hiddenFees", "source", "sourceLogo"])
    
    if not df.empty:
        df["price_numeric"] = df["price"].apply(lambda x: util_extract_price(str(x)))
        df = df.drop(columns=["price_numeric"])
    
    # Filtrer les produits sans description ou sans URL
    records = [r for r in df.to_dict(orient="records") if r.get("description") != "N/A" and r.get("productURL") != "N/A"]
    
    return records

