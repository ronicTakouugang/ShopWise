# routes/

Ce dossier contient les **Blueprints Flask** : la traduction HTTP <-> appels aux
`services/`. C'est la couche la plus fine du projet.

## Règles

- Une route ne contient **aucune logique métier** : elle lit `request`/`session`,
  appelle une fonction de `services/`, et retourne un `jsonify(...)`. Toute
  décision (calculs, règles métier, accès aux scrapers) vit dans `services/`.
- Une route peut lire/écrire `session` (contrairement à `services/`, qui ne
  connaît pas Flask) : c'est le seul endroit où `session` doit apparaître.
- Un fichier par domaine fonctionnel (`auth_routes.py`, `search_routes.py`...),
  jamais un fichier `routes.py` unique.
- Chaque fichier expose un `Blueprint` et rien d'autre ; `routes/__init__.py`
  centralise l'enregistrement de tous les blueprints sur l'app.

## Qui appelle qui

`routes/` → `services/` → `repositories/` → `database.py`. Une route n'appelle
jamais directement un repository ou un scraper.
