"""
Alertes de baisse de prix : récupération du prix actuel d'un produit suivi,
vérification périodique des abonnements, envoi des alertes (email + in-app).
"""
import logging
import smtplib
from concurrent.futures import ThreadPoolExecutor, wait as futures_wait
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config
from repositories import (
    articles_repository,
    notifications_repository,
    price_history_repository,
    profile_repository,
    subscriptions_repository,
)
from scrapers.auchan_scraper import scrape_auchan
from scrapers.glotehlo_scraper import scrape_glotelho
from scrapers.leclerc_scraper import scrape_leclerc
from scrapers.materielnet_scraper import scrape_materielnet
from utils import extract_price, format_price

# Sources pour lesquelles on relance un vrai scraping lors du price-check automatique.
# Amazon en est exclu : c'est un site déjà sujet au rate-limit (cf. timeouts de
# scraping), et relancer une recherche complète par produit abonné toutes les 2h y
# ajouterait trop de volume. Pour cette source, on se contente du dernier prix connu
# (mis à jour uniquement quand l'utilisateur relance une recherche manuelle).
_LIVE_RECHECK_SCRAPERS = {
    "Glotehlo": scrape_glotelho,
    "E.Leclerc": scrape_leclerc,
    "Auchan": scrape_auchan,
    "Materiel.net": scrape_materielnet,
}

# Délai global pour récupérer le prix actuel de tous les abonnements, en parallèle.
# Sous la limite de 60s du worker gunicorn (voir Dockerfile) avec une marge : sans
# ça, un scraping lent sur un seul abonnement peut faire dépasser ce délai et tuer
# toute la requête HTTP de /check_prices sans réponse (le job planifié toutes les
# 2h n'est lui pas concerné, il tourne en tâche de fond hors requête HTTP).
PRICE_CHECK_TIMEOUT_SECONDS = 45


def parse_threshold_percent(raw_threshold) -> float | None:
    """
    Convertit la valeur de seuil reçue du client en float, ou None si absente/invalide.
    None signifie "alerte dès la moindre baisse" (pas de seuil minimal).
    """
    if raw_threshold is None:
        return None
    try:
        threshold = float(raw_threshold)
        return threshold if threshold > 0 else None
    except (TypeError, ValueError):
        return None


def get_current_price(product_url: str) -> float:
    """
    Récupère le prix actuel d'un produit abonné.
    - Glotelho/Leclerc/Auchan/Materiel.net : relance une recherche par mot-clé (le nom du
      produit) et retrouve la ligne correspondant à productURL pour en extraire le prix réel.
    - Amazon/autre : retourne le dernier prix connu (articles.last_price), sans relancer
      de scraping automatique.
    - Si le produit n'est pas retrouvé (ex: disparu du site), retourne aussi last_price
      pour ne pas déclencher de fausse alerte de baisse.
    """
    try:
        article = articles_repository.get_article_by_url(product_url)
        if article is None:
            return float('inf')

        last_price = article["last_price"] if article["last_price"] is not None else float('inf')
        scraper = _LIVE_RECHECK_SCRAPERS.get(article["source"])
        if scraper is None or not article["description"]:
            return last_price

        records = scraper(article["description"]) or []
        for record in records:
            if str(record.get("productURL", "")).strip() == product_url:
                price = extract_price(str(record.get("price", "")))
                return price if price != float('inf') else last_price

        return last_price
    except Exception as e:
        logging.error("Erreur lors de la récupération du prix pour '%s': %s", product_url, e)
        return float('inf')


def send_email_alert(email: str, product_url: str, current_price: float) -> None:
    """
    Envoie un email d'alerte lorsque le prix d'un produit a baissé.
    Utilise le serveur SMTP configuré (voir config.py).
    """
    if not all([config.SMTP_SERVER, config.SMTP_USERNAME, config.SMTP_PASSWORD, config.SMTP_FROM_EMAIL]):
        logging.error("Configuration SMTP manquante : impossible d'envoyer l'email d'alerte.")
        return
    subject = "Alerte: Le prix de votre produit a baissé!"
    body = (f"Bonjour,\n\nLe prix de l'article suivant a baissé : {product_url}\n"
            f"Nouveau prix : {format_price(current_price)}\n\nCordialement,\nVotre équipe")
    message = MIMEMultipart()
    message["From"] = config.SMTP_FROM_EMAIL
    message["To"] = email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.send_message(message)
        logging.info("Email envoyé à %s", email)
    except Exception as e:
        logging.error("Erreur lors de l'envoi de l'email à %s: %s", email, e)


def _fetch_current_prices(subscriptions: list) -> dict:
    """
    Récupère le prix actuel de chaque abonnement en parallèle, sous un délai global
    (PRICE_CHECK_TIMEOUT_SECONDS). Un abonnement dont la vérification n'a pas fini à
    temps est simplement absent du dict retourné : il sera retenté au prochain passage
    (toutes les 2h, ou au prochain appel manuel de /check_prices), sans jamais bloquer
    les abonnements plus rapides.
    """
    if not subscriptions:
        return {}

    executor = ThreadPoolExecutor(max_workers=min(10, len(subscriptions)))
    try:
        futures = {executor.submit(get_current_price, sub["product_url"]): sub for sub in subscriptions}
        done, not_done = futures_wait(futures.keys(), timeout=PRICE_CHECK_TIMEOUT_SECONDS)

        current_prices = {}
        for future in done:
            sub = futures[future]
            try:
                current_prices[sub["id"]] = future.result()
            except Exception as e:
                logging.error("Erreur lors de la vérification de '%s': %s", sub["product_url"], e)

        for future in not_done:
            sub = futures[future]
            logging.warning(
                "Vérification de '%s' trop lente (> %ds), reportée au prochain passage.",
                sub["product_url"], PRICE_CHECK_TIMEOUT_SECONDS
            )
        return current_prices
    finally:
        executor.shutdown(wait=False)


def run_price_check() -> list:
    """
    Vérifie si le prix des produits abonnés a baissé.
    Envoie un email d'alerte, une notification in-app et met à jour la BDD.
    """
    try:
        subscriptions = subscriptions_repository.get_all_subscriptions()
        current_prices = _fetch_current_prices(subscriptions)

        alerts_triggered = []
        for subscription in subscriptions:
            # Accès par nom de colonne plutôt que déballage positionnel : une ligne
            # Postgres (RealDictRow) n'est pas un tuple, contrairement à sqlite3.Row.
            sub_id = subscription["id"]
            product_url = subscription["product_url"]
            baseline_price = subscription["initial_price"]
            email = subscription["email"]
            threshold_percent = subscription["threshold_percent"]

            current_price = current_prices.get(sub_id, float('inf'))
            if current_price == float('inf'):
                # Produit introuvable, vérification en erreur, ou trop lente pour ce
                # passage : on ignore ce tour plutôt que de polluer l'historique.
                continue

            # Enregistrer systématiquement dans l'historique
            price_history_repository.insert_price_point(product_url, current_price)

            if current_price < baseline_price:
                drop_percent = (baseline_price - current_price) / baseline_price * 100
                # threshold_percent NULL = comportement historique (toute baisse alerte).
                meets_threshold = threshold_percent is None or drop_percent >= threshold_percent
                if not meets_threshold:
                    continue

                # Alerte Email (respecte la préférence utilisateur)
                if profile_repository.get_email_notifications_enabled(email):
                    send_email_alert(email, product_url, current_price)

                # Alerte In-App (toujours envoyée, ce n'est pas ce que contrôle la case profil)
                message = f"Le prix du produit a baissé à {format_price(current_price)} !"
                notifications_repository.insert_notification(email, message, product_url)

                alerts_triggered.append({
                    "subscription_id": sub_id,
                    "email": email,
                    "product_url": product_url,
                    "current_price": format_price(current_price),
                    "previous_price": format_price(baseline_price)
                })
                subscriptions_repository.update_subscription_reference_price(sub_id, current_price)

        logging.info("Vérification terminée. Alertes déclenchées : %s", alerts_triggered)
        return alerts_triggered
    except Exception as e:
        logging.error("Erreur lors de la vérification des prix: %s", e)
        return []
