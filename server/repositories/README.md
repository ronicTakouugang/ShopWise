# repositories/

Ce dossier est le **seul endroit du projet où `database.get_connection()` (SQLite)
est appelé**. Chaque fichier correspond à une table (ou un petit groupe de tables
étroitement liées) et n'expose que des fonctions simples : une fonction = une
requête (ou une petite suite de requêtes qui n'a de sens que groupée, comme un
"lire ou créer par défaut").

## Règles

- **Aucune logique métier ici** : pas de calcul de pertinence, pas de décision
  d'envoyer un email, pas d'appel à un scraper. Une fonction repository répond à
  la question "comment je lis/écris cette donnée ?", jamais "que dois-je faire
  avec ?".
- **Aucun `import flask`** : ces fonctions ne connaissent ni `request`, ni
  `session`, ni `jsonify`. Elles prennent des valeurs simples en paramètre
  (email, productURL, ...) et retournent des dicts/listes/valeurs simples.
- Nom des fonctions : verbe + nom (`get_favorites_by_email`, `insert_favorite`,
  `delete_favorite`), jamais un nom vague comme `handle` ou `process`.
- Si une fonction aurait besoin de plus de 3 paramètres pour des données liées
  entre elles (ex: tous les champs d'un favori), elle prend un seul dict en
  paramètre plutôt que d'empiler les paramètres.

## Qui appelle qui

`routes/` → `services/` → `repositories/` → `database.py`. Un repository
n'appelle jamais un service ni une route (ça créerait une dépendance circulaire).
