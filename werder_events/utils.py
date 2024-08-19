import logging
import sqlite3


def setup_logger(name, verbose):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger



def create_database(db_path, logger=None):
    if logger:
        logger.debug(f"Creating/connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT,
        start_date TEXT,
        end_date TEXT,
        location TEXT,
        description TEXT,
        event_type TEXT,
        source TEXT,
        event_hash TEXT UNIQUE,
        is_reviewed BOOLEAN DEFAULT 0,
        is_visible BOOLEAN DEFAULT 0
    )
    ''')
    conn.commit()

    if logger:
        logger.debug("Database table 'events' created/verified")
    return conn
