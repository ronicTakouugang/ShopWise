"""
Connexion à la base SQLite de l'application et création de son schéma.

Ce module ne contient aucune logique métier : uniquement l'ouverture de
connexion et la définition des tables. Les requêtes SELECT/INSERT/UPDATE/DELETE
vivent dans repositories/, jamais ici.
"""
import logging
import sqlite3

DATABASE_PATH = "subscriptions.db"


def get_connection() -> sqlite3.Connection:
    """
    Ouvre une connexion à la base SQLite de l'application.
    Les lignes se comportent comme des dictionnaires (accès par nom de colonne
    via row["colonne"], en plus de l'accès positionnel classique).
    """
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Crée toutes les tables de l'application si elles n'existent pas déjà."""
    try:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_url TEXT,
                    initial_price REAL,
                    email TEXT
                )
            """)
            # threshold_percent : baisse minimale (en %) pour déclencher une alerte.
            # NULL = comportement historique (toute baisse déclenche une alerte).
            # Ajout via ALTER (la table peut déjà exister sans cette colonne sur une
            # base créée avant cette fonctionnalité).
            cursor.execute("PRAGMA table_info(subscriptions)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if "threshold_percent" not in existing_columns:
                cursor.execute("ALTER TABLE subscriptions ADD COLUMN threshold_percent REAL")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    email TEXT PRIMARY KEY,
                    display_name TEXT,
                    notifications_enabled INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    productURL TEXT,
                    price REAL,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorite_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    name TEXT,
                    UNIQUE(email, name)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorite_list_items (
                    list_id INTEGER,
                    productURL TEXT,
                    FOREIGN KEY(list_id) REFERENCES favorite_lists(id) ON DELETE CASCADE,
                    PRIMARY KEY(list_id, productURL)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS in_app_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    message TEXT,
                    productURL TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    email TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        logging.info("Base de données initialisée avec succès.")
    except Exception as e:
        logging.error("Erreur lors de l'initialisation de la BDD: %s", e)
