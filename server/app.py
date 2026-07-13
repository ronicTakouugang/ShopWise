"""
Point d'entrée de l'application Flask : configuration, enregistrement des routes
et planification du job périodique de vérification des prix.

Toute la logique HTTP vit dans routes/ (un Blueprint par domaine fonctionnel),
toute la logique métier vit dans services/, et tout accès à la base de données
vit dans repositories/. Ce fichier ne fait que construire l'app et l'assembler.
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from flask_cors import CORS

import config
from database import initialize_database
from extensions import limiter
from routes import register_blueprints
from services import price_alert_service

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY

# Configuration des cookies de session
app.config.update(
    SESSION_COOKIE_SECURE=config.SESSION_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

CORS(app, supports_credentials=True, origins=config.CORS_ALLOWED_ORIGINS)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

initialize_database()
limiter.init_app(app)
register_blueprints(app)


#########################
# Lancement de l'application et du job planifié
#########################
if __name__ == "__main__":
    # En debug, le reloader Flask relance ce script dans un sous-processus : sans ce garde,
    # le scheduler démarrerait deux fois (process parent + enfant) et doublerait le rythme
    # réel des price-checks.
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=price_alert_service.run_price_check, trigger="interval", hours=2)
        scheduler.start()
    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    except (KeyboardInterrupt, SystemExit):
        pass
