import re
import logging
import random
import time
from curl_cffi import requests as curl_requests
from deep_translator import GoogleTranslator

def get_robust_headers(accept_language: str = "en-US,en;q=0.9"):
    """
    Génère des headers complets pour imiter un vrai navigateur.
    Pas de User-Agent ici : curl_cffi l'injecte automatiquement en cohérence avec le
    paramètre `impersonate` (ex: chrome120). Le fixer nous-mêmes avec un UA aléatoire
    (potentiellement mobile/Safari/vieux Chrome) alors que l'empreinte TLS reste figée
    sur Chrome 120 crée une incohérence facilement détectable par les anti-bots.
    """
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": accept_language,
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def robust_request(url, method="GET", impersonate="chrome120", timeout=30, max_retries=3, accept_language="en-US,en;q=0.9", **kwargs):
    """
    Effectue une requête HTTP robuste en utilisant curl_cffi pour l'empreinte TLS.
    Réutilise une même session (donc les mêmes cookies et la même connexion) entre les
    tentatives d'un même appel : un vrai navigateur qui réessaie garde son identité, il
    n'apparaît pas comme un nouveau visiteur à chaque retry.
    """
    custom_headers = kwargs.pop('headers', None)
    headers = get_robust_headers(accept_language)
    if custom_headers:
        headers.update(custom_headers)

    session = curl_requests.Session()
    try:
        for attempt in range(max_retries):
            try:
                # Délai aléatoire plus long pour simuler l'humain
                if attempt > 0:
                    wait_time = random.uniform(5, 10)
                    logging.info(f"⏳ Attente de {wait_time:.2f}s avant tentative {attempt+1}...")
                    time.sleep(wait_time)
                else:
                    time.sleep(random.uniform(1, 3))

                response = session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    impersonate=impersonate,
                    timeout=timeout,
                    **kwargs
                )

                if response.status_code == 200:
                    # Vérification sommaire si on est bloqué par un CAPTCHA ou page vide
                    content_len = len(response.content)
                    if content_len < 1000:
                        logging.warning(f"⚠️ Réponse suspecte (trop courte: {content_len} bytes) pour {url}")
                    return response
                elif response.status_code == 403:
                    logging.warning(f"🚫 Accès refusé (403) pour {url}. Tentative {attempt+1}/{max_retries}")
                elif response.status_code == 429:
                    logging.warning(f"⏳ Rate limited (429) pour {url}. Tentative {attempt+1}/{max_retries}")
                else:
                    logging.error(f"❌ Erreur HTTP {response.status_code} pour {url}")

            except Exception as e:
                logging.error(f"❌ Exception lors de la requête vers {url} : {e}")
    finally:
        session.close()

    return None

def normalize_text(text: str) -> str:
    """Normalise le texte en le mettant en minuscule et en conservant les espaces."""
    if not text:
        return ""
    import unicodedata
    # Enlève les accents
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    # Met en minuscule et garde seulement alphanumérique et espaces
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()

def extract_price(price_str: str) -> float:
    """
    Extrait le prix numérique à partir d'une chaîne.
    Gère les symboles €, $ et les séparateurs de milliers.
    """
    if not price_str or price_str == "N/A":
        return float('inf')
    try:
        # Si la chaîne contient seulement des lettres (comme "Ships to France"), on ignore
        if not re.search(r'\d', price_str):
            return float('inf')
            
        # Nettoyage de la chaîne
        # On enlève les espaces
        cleaned = price_str.replace(" ", "").replace("\u00a0", "").strip()
        
        # Gestion du format français (1.234,56) vs US (1,234.56)
        # Si on a un point et une virgule, on suppose que le point est le séparateur de milliers
        if "." in cleaned and "," in cleaned:
            if cleaned.find(".") < cleaned.find(","):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # S'il n'y a qu'une virgule, on vérifie si c'est un séparateur décimal (ex: 29,99) 
            # ou de milliers (ex: 1,000)
            # Dans le contexte Euro/FCFA, c'est souvent un séparateur décimal
            # Mais attention au format 1,234.56 (déjà géré au dessus)
            # Si la virgule est suivie de 2 chiffres à la fin, c'est probablement décimal
            if len(cleaned.split(",")[-1]) == 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")

        # On garde seulement les chiffres et le point décimal
        numeric_str = re.sub(r'[^\d.]', '', cleaned)
        if not numeric_str or numeric_str == ".":
            return float('inf')
        return float(numeric_str)
    except Exception as e:
        logging.error("Erreur d'extraction du prix pour '%s': %s", price_str, e)
        return float('inf')

def format_price(price_value: float) -> str:
    """Formate une valeur de prix."""
    try:
        if price_value == float('inf'):
            return "N/A"
        return "{:,.2f}".format(price_value)
    except Exception as e:
        logging.error("Erreur de formatage pour le prix %s: %s", price_value, e)
        return "N/A"

def translate_to_english(text: str) -> str:
    """
    Traduit un texte en anglais si nécessaire.
    """
    if not text:
        return ""
    try:
        # On tente de traduire. Si c'est déjà en anglais, GoogleTranslator gère généralement bien.
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        logging.info(f"Traduction: '{text}' -> '{translated}'")
        return translated
    except Exception as e:
        logging.error(f"Erreur lors de la traduction de '{text}': {e}")
        return text

def convert_to_euro(price_str: str) -> str:
    """
    Convertit un montant (FCFA, $, £) en Euro (€).
    """
    if not price_str or price_str == "N/A":
        return "N/A"
    
    price_str = price_str.strip().replace("\u00a0", " ")
    
    # Taux de conversion (approximatifs)
    FCFA_TO_EURO = 1 / 655.957
    USD_TO_EURO = 0.92
    GBP_TO_EURO = 1.17
    
    try:
        # Si la chaîne contient seulement des lettres, on ignore
        if not re.search(r'\d', price_str):
            return price_str
            
        # Nettoyage pour extraction numérique
        numeric_part = re.sub(r'[^\d,.]', '', price_str)
        if ',' in numeric_part and '.' in numeric_part:
            numeric_part = numeric_part.replace(',', '')
        elif ',' in numeric_part:
            numeric_part = numeric_part.replace(',', '.')
            
        val = float(numeric_part)
        
        # Détection de la devise et conversion
        if "FCFA" in price_str or "CFA" in price_str:
            val = val * FCFA_TO_EURO
        elif "$" in price_str or "USD" in price_str:
            val = val * USD_TO_EURO
        elif "£" in price_str or "GBP" in price_str:
            val = val * GBP_TO_EURO
        elif "EUR" in price_str or "€" in price_str:
            # Déjà en Euro, on garde la valeur telle quelle
            pass
        else:
            # Par défaut, si aucune devise n'est détectée mais que le montant est très élevé,
            # on suppose que c'est du FCFA (cas fréquent sur Glotelho sans symbole)
            if val > 5000:
                val = val * FCFA_TO_EURO
        
        return "{:,.2f} €".format(val)
    except Exception as e:
        logging.error(f"Erreur conversion Euro pour '{price_str}': {e}")
        return price_str
