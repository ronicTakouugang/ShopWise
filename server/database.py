"""
Connexion à la base de données de l'application et création de son schéma.

Deux moteurs supportés : SQLite en local (par défaut) et Postgres en production
(quand config.DATABASE_URL est défini, ex: fourni automatiquement par l'addon
Postgres de Render). Ce module ne contient aucune logique métier : uniquement
l'ouverture de connexion et la définition des tables. Les requêtes
SELECT/INSERT/UPDATE/DELETE vivent dans repositories/, jamais ici.

Pour que repositories/ n'ait pas à connaître le moteur utilisé, get_connection()
retourne toujours un objet exposant .execute(query, params) avec des placeholders
'?' (comme sqlite3), même sur Postgres : _PostgresConnection traduit '?' en '%s'
avant d'exécuter. Cette traduction naïve suppose qu'aucune requête ne contient un
'?' littéral hors placeholder, ce qui est le cas de toutes les requêtes de ce
projet (pas de JSON ni de LIKE avec '?' comme caractère de données).

Sur Postgres, les connexions viennent d'un pool (voir _get_pg_pool) plutôt que
d'un psycopg2.connect() par appel : chaque repository ouvre/ferme une connexion
à chaque fonction (get_connection() par requête), ce qui est gratuit sur SQLite
(fichier local) mais coûte un aller-retour réseau + handshake TLS sur Postgres.
En pratique, persist_articles() (appelée après chaque recherche, jusqu'à ~180
lignes) sans pool a fait dépasser le timeout gunicorn de 60s en production - le
pool réutilise des connexions déjà établies au lieu d'en ouvrir une nouvelle
à chaque fois.
"""
import logging
import sqlite3
from datetime import datetime, timedelta

import config

DATABASE_PATH = "subscriptions.db"

IS_POSTGRES = bool(config.DATABASE_URL)

_pg_pool = None


def _get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        import psycopg2.extras
        import psycopg2.pool
        # Conservateur (maxconn=5) : les instances Postgres gratuites (Render, etc.)
        # plafonnent souvent le nombre de connexions simultanées assez bas.
        _pg_pool = psycopg2.pool.ThreadedConnectionPool(
            1, 5, config.DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor
        )
    return _pg_pool


class _PostgresConnection:
    """Enveloppe une connexion psycopg2 issue du pool pour exposer la même API
    que sqlite3.Connection (.execute() direct sur la connexion, lignes
    accessibles par nom de colonne), et la restitue au pool en fin de vie au
    lieu de fermer la connexion TCP sous-jacente."""

    def __init__(self, raw_connection, pool):
        self._raw = raw_connection
        self._pool = pool

    def execute(self, query: str, params: tuple = ()):
        cursor = self._raw.cursor()
        cursor.execute(query.replace("?", "%s"), params)
        return cursor

    def cursor(self):
        return self._raw.cursor()

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._pool.putconn(self._raw)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._raw.commit()
        else:
            self._raw.rollback()
        self._pool.putconn(self._raw)


def get_connection():
    """
    Ouvre une connexion à la base de l'application (Postgres si config.DATABASE_URL
    est défini, SQLite sinon). Les lignes se comportent comme des dictionnaires
    (accès par nom de colonne via row["colonne"]) dans les deux cas.
    """
    if IS_POSTGRES:
        pool = _get_pg_pool()
        raw_connection = pool.getconn()
        return _PostgresConnection(raw_connection, pool)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_threshold_percent_column(connection) -> None:
    """
    Ajoute la colonne subscriptions.threshold_percent si elle n'existe pas déjà
    (une base créée avant cette fonctionnalité peut en être dépourvue).
    """
    if IS_POSTGRES:
        cursor = connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'subscriptions'"
        )
        existing_columns = {row["column_name"] for row in cursor.fetchall()}
    else:
        cursor = connection.execute("PRAGMA table_info(subscriptions)")
        existing_columns = {row[1] for row in cursor.fetchall()}

    if "threshold_percent" not in existing_columns:
        connection.execute("ALTER TABLE subscriptions ADD COLUMN threshold_percent REAL")


def _ensure_product_group_id_column(connection) -> None:
    """
    Ajoute la colonne articles.product_group_id si elle n'existe pas déjà (une base
    créée avant le rapprochement produit inter-enseigne peut en être dépourvue).
    """
    if IS_POSTGRES:
        cursor = connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'articles'"
        )
        existing_columns = {row["column_name"] for row in cursor.fetchall()}
    else:
        cursor = connection.execute("PRAGMA table_info(articles)")
        existing_columns = {row[1] for row in cursor.fetchall()}

    if "product_group_id" not in existing_columns:
        connection.execute("ALTER TABLE articles ADD COLUMN product_group_id INTEGER")


def initialize_database() -> None:
    """Crée toutes les tables de l'application si elles n'existent pas déjà."""
    # SERIAL (Postgres) et INTEGER PRIMARY KEY AUTOINCREMENT (SQLite) sont les deux
    # syntaxes d'auto-incrément de clé primaire ; le reste du DDL est portable tel quel.
    id_pk = "id SERIAL PRIMARY KEY" if IS_POSTGRES else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    try:
        with get_connection() as connection:
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    {id_pk},
                    product_url TEXT,
                    initial_price REAL,
                    email TEXT
                )
            """)
            # threshold_percent : baisse minimale (en %) pour déclencher une alerte.
            # NULL = comportement historique (toute baisse déclenche une alerte).
            _ensure_threshold_percent_column(connection)
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS favorites (
                    {id_pk},
                    email TEXT,
                    description TEXT,
                    price TEXT,
                    imageURL TEXT,
                    productURL TEXT,
                    source TEXT,
                    sourceLogo TEXT,
                    rating TEXT,
                    reviewCount TEXT,
                    UNIQUE(email, productURL)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    email TEXT PRIMARY KEY,
                    display_name TEXT,
                    notifications_enabled INTEGER DEFAULT 1
                )
            """)
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS price_history (
                    {id_pk},
                    productURL TEXT,
                    price REAL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS favorite_lists (
                    {id_pk},
                    email TEXT,
                    name TEXT,
                    UNIQUE(email, name)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS favorite_list_items (
                    list_id INTEGER,
                    productURL TEXT,
                    FOREIGN KEY(list_id) REFERENCES favorite_lists(id) ON DELETE CASCADE,
                    PRIMARY KEY(list_id, productURL)
                )
            """)
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS in_app_notifications (
                    {id_pk},
                    email TEXT,
                    message TEXT,
                    productURL TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read INTEGER DEFAULT 0
                )
            """)
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS product_groups (
                    {id_pk},
                    canonical_title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Une ligne par mot significatif de la description d'origine (voir
            # services/product_matching_service.py) : sert de "blocking" pour le
            # rapprochement (candidats = groupes partageant au moins un mot), plutôt
            # que de comparer une nouvelle description à tous les groupes connus.
            connection.execute("""
                CREATE TABLE IF NOT EXISTS product_group_words (
                    group_id INTEGER,
                    word TEXT,
                    FOREIGN KEY(group_id) REFERENCES product_groups(id) ON DELETE CASCADE,
                    PRIMARY KEY(group_id, word)
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    productURL TEXT PRIMARY KEY,
                    description TEXT,
                    imageURL TEXT,
                    source TEXT,
                    sourceLogo TEXT,
                    rating TEXT,
                    reviewCount TEXT,
                    last_price REAL,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # product_group_id : rapprochement heuristique inter-enseigne (voir
            # services/product_matching_service.py), ajouté après coup -> colonne
            # optionnelle plutôt que dans le CREATE TABLE ci-dessus.
            _ensure_product_group_id_column(connection)
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS search_log (
                    {id_pk},
                    query TEXT,
                    email TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        logging.info("Base de données initialisée avec succès (%s).", "Postgres" if IS_POSTGRES else "SQLite")
    except Exception as e:
        logging.error("Erreur lors de l'initialisation de la BDD: %s", e)


def recent_cutoff(days: int) -> datetime:
    """
    Calcule l'horodatage de coupure pour "les N derniers jours", en Python plutôt
    qu'en SQL, pour rester portable entre SQLite et Postgres (leurs fonctions de
    date respectives ne sont pas compatibles). Naïf (sans fuseau horaire) en UTC,
    pour correspondre exactement au format stocké par CURRENT_TIMESTAMP dans les
    deux moteurs (colonnes TIMESTAMP sans fuseau horaire).
    """
    return datetime.utcnow() - timedelta(days=days)
