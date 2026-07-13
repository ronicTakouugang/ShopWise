# services/

Ce dossier contient la **logique métier** de l'application : recherche/scraping,
alertes de baisse de prix, authentification. C'est la couche qui décide *quoi
faire*, entre les routes (qui décident *comment répondre en HTTP*) et les
repositories (qui décident *comment lire/écrire en base*).

## Règles

- **Aucun `import flask`** : pas de `request`, `session`, ni `jsonify` ici. Une
  fonction de service reçoit des valeurs simples en paramètre (query, email,
  productURL...) et retourne des valeurs simples (dict, liste, nombre...). Ça
  rend chaque fonction testable indépendamment d'une requête HTTP.
- Les services peuvent appeler des `repositories/` et des `scrapers/`, mais
  jamais l'inverse.
- Nom des fonctions : verbe + nom (`do_search`, `run_price_check`,
  `send_email_alert`), jamais un nom vague comme `handle` ou `process`.

## Qui appelle qui

`routes/` → `services/` → `repositories/` → `database.py`. Un service
n'appelle jamais une route (ça créerait une dépendance circulaire).

## Contenu

- `search_service.py` : recherche produits (orchestration des scrapers, cache
  court, calcul de pertinence, persistance du catalogue).
- `price_alert_service.py` : récupération du prix actuel d'un produit suivi,
  vérification périodique des abonnements, envoi des alertes (email + in-app).
- `auth_service.py` : fine surcouche autour de Firebase (Pyrebase) pour
  inscription/connexion/réinitialisation de mot de passe.
