# Image de production pour le serveur Flask ShopWise.
# Sert via gunicorn (pas le serveur de dev Flask) avec un seul worker : le job
# planifié de vérification des prix (APScheduler) démarre au niveau module dans
# app.py, et plusieurs workers démarreraient chacun leur propre scheduler.
FROM python:3.11-slim

WORKDIR /app

# psycopg2-binary embarque déjà libpq, donc pas besoin de libpq-dev ici.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5000
EXPOSE 5000

# Forme shell (pas exec) pour que $PORT soit interpolé : Render l'injecte
# dynamiquement au démarrage, ce n'est pas toujours 5000.
CMD gunicorn --workers 1 --bind 0.0.0.0:$PORT --timeout 60 app:app
