"""
ClashBoard — Timetable Clash Resolver & Adaptive Study Planner.
Main application entry point.

Hard constraints met:
- Tkinter only with ttk themed widgets (theme: 'clam')
- SQLite via Python's built-in sqlite3 with foreign keys enforced
- Layered architecture: db/ (queries only), services/ (pure logic), gui/ (Tkinter)
- Auto-seeds realistic demo data on first run
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_connection
from db.schema import init_db
from db.seed import seed_database
from gui.app import ClashBoardApp


def main():
    # 1. Establish SQLite connection with foreign keys enforced
    conn = get_connection()

    # 2. Initialize database schema (6 tables)
    init_db(conn)

    # 3. Auto-seed realistic demo data on first run
    seed_database(conn)

    # 4. Launch GUI Application
    app = ClashBoardApp(conn)
    try:
        app.mainloop()
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

