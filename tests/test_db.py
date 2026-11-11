"""
Unit tests for Database layer — updated for 7-subject seed and day_order schema.
"""
import pytest
import sqlite3
from db.connection import get_connection
from db.schema import init_db
from db import queries
from db.seed import seed_database


@pytest.fixture
def memory_db():
    conn = get_connection(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def test_init_db(memory_db):
    cursor = memory_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    for expected in ("Subjects", "Timetable", "Exams", "Topics", "StudySessions", "Clashes", "Settings"):
        assert expected in tables


def test_subject_crud(memory_db):
    sid = queries.insert_subject(memory_db, "Algorithms", "CS301", 4, 4)
    assert sid is not None

    sub = queries.get_subject_by_id(memory_db, sid)
    assert sub["name"] == "Algorithms"
    assert sub["difficulty_level"] == 4

    queries.update_subject(memory_db, sid, "Advanced Algorithms", "CS301", 5, 4)
    assert queries.get_subject_by_id(memory_db, sid)["difficulty_level"] == 5

    queries.delete_subject(memory_db, sid)
    assert queries.get_subject_by_id(memory_db, sid) is None


def test_foreign_key_enforcement(memory_db):
    with pytest.raises(sqlite3.IntegrityError):
        queries.insert_timetable_slot(memory_db, 9999, 1, "10:00", "11:00", "Room")


def test_seed_database(memory_db):
    seeded = seed_database(memory_db)
    assert seeded is True

    subs = queries.get_all_subjects(memory_db)
    assert len(subs) == 7           # DS, T&T, OS, PE, UHV, CO, AP

    slots = queries.get_all_timetable_slots(memory_db)
    assert len(slots) == 26         # exact count from seed (image: 6+6+5+6+3=26)

    exams = queries.get_all_exams(memory_db)
    assert len(exams) == 5

    clashes = queries.get_all_clashes(memory_db)
    assert len(clashes) > 0         # intentional T&T/OS exam-exam clash seeded

    sessions = queries.get_all_study_sessions(memory_db)
    assert len(sessions) > 0
    assert any(s['status'] == 'done' for s in sessions)

    # Day order entries must use integers 1–5, not weekday strings
    for slot in slots:
        assert isinstance(slot['day_order'], int)
        assert 1 <= slot['day_order'] <= 5
