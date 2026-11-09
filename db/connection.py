import os
import sqlite3

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clashboard.db")


def get_connection(db_path=None):
    """
    Returns a connection to the SQLite database with foreign keys enabled
    and sqlite3.Row row factory for column-name indexing.
    """
    path = db_path if db_path is not None else DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

