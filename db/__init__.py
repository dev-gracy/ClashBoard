"""
Database package for ClashBoard.
Provides connection management, schema initialization, and queries.
"""
from db.connection import get_connection, DEFAULT_DB_PATH
from db.schema import init_db

__all__ = ["get_connection", "DEFAULT_DB_PATH", "init_db"]

