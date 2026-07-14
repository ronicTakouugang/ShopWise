"""
Recherche de produits : orchestration des scrapers, calcul de pertinence,
cache court, persistance du catalogue, et marquage favoris/abonnements.
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait as futures_wait

from repositories import (
    articles_repository,
    favorites_repository,
    price_history_repository,
    search_log_repository,
    subscriptions_repository,
)
from scrapers.amazon_scraper import scrape_amazon
from scrapers.auchan_scraper import scrape_auchan
from scrapers.glotehlo_scraper import scrape_glotelho
from scrapers.leclerc_scraper import scrape_leclerc
from scrapers.walmart_scraper import scrape_walmart
from utils import extract_price, normalize_text

# Délai maximum accordé à un site pour répondre avant qu'on l'écarte de la recherche.
# Mesuré en conditions réelles : Amazon/Glotelho/Auchan/Leclerc terminent tous en
# moins de 6s ; seul Walmart (anti-bot systématique) dépassait largement ce délai
# pour 0 résultat, ce qui plombait la durée de TOUTE recherche à ~15-19s. Abaissé
# à 8s (marge au-dessus des ~6s mesurés) plutôt que de retarder chaque recherche
# pour un site qui ne contribue de toute façon quasiment jamais de résultats.
SCRAPER_TIMEOUT_SECONDS = 8

# Réduit le nombre de requêtes réellement envoyées aux sites pour des recherches
# identiques/répétées (moins de volume = moins de risque de blocage), sans jamais
# ralentir une recherche : un cache "hit" est immédiat, un "miss" se comporte
# exactement comme avant.
SEARCH_CACHE_TTL_SECONDS = 600  # 10 minutes
_search_cache = {}
_search_cache_lock = threading.Lock()


def compute_deal_attributes(record: dict, query: str = "") -> dict:
    """Calcule et ajoute les attributs de l'offre et le score de pertinence composite."""
    num_price = extract_price(str(record.get("price", "")))
    # Remplacer Infinity par une valeur numérique finie très élevée pour le JSON
    if num_price == float('inf'):
        record["numeric_price"] = 999999999.0
    else:
        record["numeric_price"] = num_price

    # Calcul de la pertinence
    relevance_score = 0
    if query:
        query_words = normalize_text(query).lower().split()
        description = normalize_text(record.get("description", "")).lower()

        # 1. Correspondance textuelle (Score de base)
        matches = 0
        for word in query_words:
            if word in description:
                matches += 1
                # Bonus si le mot est au début de la description
                if description.startswith(word):
                    relevance_score += 1.0

        # Score basé sur le ratio de mots trouvés
        if query_words:
            relevance_score += (matches / len(query_words)) * 5.0

        # 2. Qualité des données (Bonus)
        # Bonus si une image est présente
        if record.get("imageURL") and record.get("imageURL") != "N/A":
            relevance_score += 2.0

        # Bonus si le prix est valide (pas infini)
        if num_price != float('inf'):
            relevance_score += 1.5

        # 3. Pondération par la source (Optionnel, ex: Amazon souvent plus fiable)
        if record.get("source") == "Amazon":
            relevance_score += 0.5

        # 4. Popularité (Bonus)
        popularity = record.get("popularity", 0)
        if popularity > 1000:
            relevance_score += 1.0
        elif popularity > 100:
            relevance_score += 0.5

    record["relevance_score"] = round(relevance_score, 2)
    return record


def persist_articles(records: list) -> None:
    """
    Met à jour le catalogue d'articles et enregistre un point d'historique de prix
    pour chaque produit ramené par une recherche réelle (hors cache).
    Un nouveau point n'est ajouté à price_history que si le prix a changé par
    rapport au dernier point connu, pour éviter de saturer l'historique de points
    identiques à chaque recherche.
    """
    try:
        for record in records:
            product_url = str(record.get("productURL", "")).strip()
            numeric_price = record.get("numeric_price", float('inf'))
            if not product_url or numeric_price == float('inf'):
                continue
            if numeric_price <= 0 or numeric_price > articles_repository.MAX_PLAUSIBLE_PRICE_EUR:
                logging.warning(
                    "Prix invraisemblable ignoré pour '%s' (%s): %s",
                    record.get("description"), product_url, numeric_price
                )
                continue

            articles_repository.upsert_article(
                product_url,
                record.get("description"),
                record.get("imageURL"),
                record.get("source"),
                record.get("sourceLogo"),
                record.get("rating"),
                record.get("reviewCount"),
                numeric_price,
            )

            last_price = price_history_repository.get_last_price_point(product_url)
            if last_price is None or last_price != numeric_price:
                price_history_repository.insert_price_point(product_url, numeric_price)
    except Exception as e:
        logging.error("Erreur lors de la persistance des articles: %s", e)


def do_search(query: str) -> list:
    """
    Effectue une recherche de produits à partir d'un mot-clé en utilisant plusieurs scrapers.
    Retourne une liste de produits filtrés et triés par prix.
    Les scrapers tournent en parallèle sous un délai commun : un site lent ou en erreur
    est simplement écarté, sans jamais retarder les résultats des autres sites.
    """
    executor = ThreadPoolExecutor(max_workers=5)
    try:
        futures = {
            executor.submit(scrape_amazon, query): "Amazon",
            executor.submit(scrape_glotelho, query): "Glotelho",
            executor.submit(scrape_walmart, query): "Walmart",
            executor.submit(scrape_leclerc, query): "Leclerc",
            executor.submit(scrape_auchan, query): "Auchan",
        }

        # Un seul délai partagé pour les 4 scrapers en même temps : un site lent
        # ne grignote plus le temps d'attente des autres (contrairement à des
        # future.result(timeout=...) enchaînés un par un).
        done, not_done = futures_wait(futures.keys(), timeout=SCRAPER_TIMEOUT_SECONDS)

        results_by_source = {}
        for future in done:
            source_name = futures[future]
            try:
                records = future.result()
                results_by_source[source_name] = records if records else []
            except Exception as e:
                logging.error("Erreur lors du scraping %s pour '%s': %s", source_name, query, e)
                results_by_source[source_name] = []

        for future in not_done:
            source_name = futures[future]
            logging.warning(
                "Le site %s n'a pas répondu en moins de %ds pour la requête '%s', "
                "il est écarté de cette recherche.", source_name, SCRAPER_TIMEOUT_SECONDS, query
            )
            results_by_source[source_name] = []

        amazon_records = results_by_source.get("Amazon", [])
        glotehlo_records = results_by_source.get("Glotelho", [])
        walmart_records = results_by_source.get("Walmart", [])
        leclerc_records = results_by_source.get("Leclerc", [])
        auchan_records = results_by_source.get("Auchan", [])
    finally:
        # wait=False : on ne bloque pas la réponse sur un scraper resté accroché en arrière-plan,
        # il se terminera de lui-même et sera simplement ignoré.
        executor.shutdown(wait=False)

    combined_results = amazon_records + glotehlo_records + walmart_records + leclerc_records + auchan_records

    filtered_results = []
    seen_urls = set()
    for record in combined_results:
        try:
            # Suppression du filtrage strict sur le prix pour permettre l'affichage de tous les produits
            # On s'assure juste que les clés minimales existent
            if not record.get("description"):
                continue

            product_url = record.get("productURL", "").strip()
            if product_url:
                if product_url in seen_urls:
                    continue
                seen_urls.add(product_url)

            record = compute_deal_attributes(record, query)
            filtered_results.append(record)
        except Exception as e:
            logging.warning("Erreur lors du traitement d'un résultat : %s", e)
            continue

    try:
        # Tri par pertinence décroissante d'abord, puis par prix croissant
        sorted_results = sorted(
            filtered_results,
            key=lambda r: (-r.get("relevance_score", 0), r.get("numeric_price", float('inf')))
        )
    except Exception as e:
        logging.error("Erreur lors du tri des résultats : %s", e)
        # En cas d'erreur de tri, retourner les résultats non triés mais fonctionnels
        sorted_results = filtered_results

    persist_articles(sorted_results)
    return sorted_results


def log_search(query: str, email: str | None) -> None:
    """Enregistre une recherche pour les statistiques (recherches les plus fréquentes)."""
    try:
        search_log_repository.insert_search_log(normalize_text(query), email)
    except Exception as e:
        logging.error("Erreur lors de l'enregistrement de la recherche: %s", e)


def do_search_cached(query: str, email: str | None) -> list:
    """Sert les résultats depuis un cache court si disponible, sinon lance do_search."""
    cache_key = normalize_text(query)
    now = time.time()
    log_search(query, email)

    with _search_cache_lock:
        cached = _search_cache.get(cache_key)
        if cached and (now - cached[0]) < SEARCH_CACHE_TTL_SECONDS:
            logging.info("Résultats servis depuis le cache pour '%s'.", query)
            return cached[1]

    results = do_search(query)

    with _search_cache_lock:
        _search_cache[cache_key] = (now, results)

    return results


def mark_favorites(results: list, email: str | None) -> list:
    """
    Retourne une copie des résultats avec isFavorite=True pour ceux déjà en favoris.
    On copie chaque enregistrement (au lieu de muter les objets reçus) car `results`
    peut être la liste partagée par le cache de recherche : sans copie, le marquage
    des favoris d'un utilisateur fuiterait vers les autres utilisateurs via le cache.
    """
    copies = [dict(r) for r in results]
    if not email:
        return copies
    try:
        favorite_urls = favorites_repository.get_favorite_urls_by_email(email)
        for record in copies:
            record["isFavorite"] = record.get("productURL") in favorite_urls
    except Exception as e:
        logging.error("Erreur lors du marquage des favoris: %s", e)
    return copies


def mark_subscriptions(results: list, email: str | None) -> list:
    """
    Retourne une copie des résultats avec isSubscribed=True pour les produits dont
    l'utilisateur suit déjà le prix (alertes activées). Copie les enregistrements
    pour la même raison que mark_favorites (résultats potentiellement partagés via
    le cache de recherche).
    """
    copies = [dict(r) for r in results]
    if not email:
        return copies
    try:
        subscribed_urls = subscriptions_repository.get_subscribed_urls_by_email(email)
        for record in copies:
            record["isSubscribed"] = record.get("productURL") in subscribed_urls
    except Exception as e:
        logging.error("Erreur lors du marquage des abonnements: %s", e)
    return copies
