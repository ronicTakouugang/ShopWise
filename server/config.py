"""
Configuration centrale de l'application : variables d'environnement, Firebase,
Flask, CORS et SMTP. Rien d'autre ne doit lire os.getenv() directement ailleurs
dans le projet : toute nouvelle variable d'environnement se déclare ici.
"""
import os

import pyrebase
from dotenv import load_dotenv

load_dotenv()

# --- Firebase (authentification) ---
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
}

# --- Flask ---
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default-secret-key")
# CORS_ORIGIN (ex: l'URL du static site Render en production) s'ajoute à localhost:4200,
# utilisé en dev, plutôt que de le remplacer.
CORS_ALLOWED_ORIGINS = ["http://localhost:4200"]
if os.getenv("CORS_ORIGIN"):
    CORS_ALLOWED_ORIGINS.append(os.getenv("CORS_ORIGIN"))
# En local (http://localhost) le cookie de session doit rester non-Secure, sinon le
# navigateur le refuse. Passer SESSION_COOKIE_SECURE=true en production (HTTPS).
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
# En local, client (localhost:4200) et serveur (localhost:5000) sont "same-site"
# (même hostname), donc SameSite=Lax suffit. En production, client et serveur sont
# sur des sous-domaines Render différents (shopwise-client.onrender.com /
# shopwise-server-xxxx.onrender.com) : pour le navigateur ce sont des sites
# différents, et SameSite=Lax bloque alors l'envoi du cookie sur les appels AJAX
# cross-site - la connexion réussit côté serveur mais le front ne le voit jamais.
# SameSite=None (à définir via env var en prod) corrige ça ; il exige Secure=true,
# déjà le cas en prod.
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

# --- Base de données ---
# Si DATABASE_URL est défini (ex: fourni automatiquement par Render pour son addon
# Postgres), la base Postgres est utilisée à la place de SQLite. Voir database.py.
DATABASE_URL = os.getenv("DATABASE_URL")

# --- SMTP (emails d'alerte de baisse de prix) ---
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")


def create_firebase_auth():
    """Initialise Firebase avec FIREBASE_CONFIG et retourne le client d'authentification."""
    firebase_app = pyrebase.initialize_app(FIREBASE_CONFIG)
    return firebase_app.auth()
