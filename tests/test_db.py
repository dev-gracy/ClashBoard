"""
Unit tests for Database layer (db/ connection, schema, queries, seed).
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
    assert "Subjects" in tables
    assert "Timetable" in tables
    assert "Exams" in tables
    assert "Topics" in tables
    assert "StudySessions" in tables
    assert "Clashes" in tables


def test_subject_crud(memory_db):
    sub_id = queries.insert_subject(memory_db, "Algorithms", "CS301", 4, 4)
    assert sub_id is not None

    sub = queries.get_subject_by_id(memory_db, sub_id)
    assert sub["name"] == "Algorithms"
    assert sub["code"] == "CS301"
    assert sub["difficulty_level"] == 4
    assert sub["credits"] == 4

    queries.update_subject(memory_db, sub_id, "Advanced Algorithms", "CS301", 5, 4)
    updated = queries.get_subject_by_id(memory_db, sub_id)
    assert updated["name"] == "Advanced Algorithms"
    assert updated["difficulty_level"] == 5

    all_subs = queries.get_all_subjects(memory_db)
    assert len(all_subs) == 1

    queries.delete_subject(memory_db, sub_id)
    assert queries.get_subject_by_id(memory_db, sub_id) is None


def test_foreign_key_enforcement(memory_db):
    # Trying to insert Timetable slot with non-existent subject_id must fail
    with pytest.raises(sqlite3.IntegrityError):
        queries.insert_timetable_slot(memory_db, 9999, "Mon", "10:00", "11:00", "L1")


def test_seed_database(memory_db):
    seeded = seed_database(memory_db)
    assert seeded is True

    # Check seeded subjects
    subs = queries.get_all_subjects(memory_db)
    assert len(subs) == 6

    # Check timetable slots
    slots = queries.get_all_timetable_slots(memory_db)
    assert len(slots) >= 14

    # Check exams
    exams = queries.get_all_exams(memory_db)
    assert len(exams) >= 3

    # Check clashes
    clashes = queries.get_all_clashes(memory_db)
    assert len(clashes) > 0

    # Check study sessions
    sessions = queries.get_all_study_sessions(memory_db)
    assert len(sessions) > 0
    # First session should be 'done'
    assert any(s['status'] == 'done' for s in sessions)

