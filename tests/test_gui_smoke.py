"""
Smoke test for ClashBoard Tkinter GUI.
Initializes Tk root, theme, all 5 screens, triggers screen switching and refresh,
then safely destroys the window without blocking.
"""
import pytest
from db.connection import get_connection
from db.schema import init_db
from db.seed import seed_database
from gui.app import ClashBoardApp


def test_gui_smoke():
    conn = get_connection(":memory:")
    init_db(conn)
    seed_database(conn)

    app = ClashBoardApp(conn)
    app.update_idletasks()

    # Verify all 5 screens were instantiated
    assert 'planner' in app.screens
    assert 'timetable' in app.screens
    assert 'clashes' in app.screens
    assert 'subjects' in app.screens
    assert 'dashboard' in app.screens

    # Test switching to each screen
    for screen_name in ['timetable', 'clashes', 'subjects', 'dashboard', 'planner']:
        app.show_screen(screen_name)
        app.update()

    # Clean up
    app.destroy()
    conn.close()

