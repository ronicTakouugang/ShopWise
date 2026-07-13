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
CORS_ALLOWED_ORIGINS = ["http://localhost:4200"]

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
