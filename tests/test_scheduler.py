"""
Unit tests for Study Scheduler service (services/scheduler.py).
Zero GUI imports, pure functions.
"""
import datetime
import pytest
from services.scheduler import compute_urgency, get_free_slots, build_schedule, reflow_on_missed
from db.connection import get_connection
from db.schema import init_db
from db.seed import seed_database
from db import queries


def test_compute_urgency():
    # priority: 5, difficulty: 5, days: 5 -> (5 * 5) / 5 = 5.0
    assert compute_urgency(5, 5, 5) == 5.0

    # days_until_exam = 1 -> (4 * 3) / 1 = 12.0
    assert compute_urgency(4, 3, 1) == 12.0

    # max(days_until_exam, 1) prevents zero division
    assert compute_urgency(4, 4, 0) == 16.0
    assert compute_urgency(4, 4, -5) == 16.0

    # Lower priority / difficulty has lower urgency
    assert compute_urgency(1, 1, 10) < compute_urgency(5, 5, 10)


def test_get_free_slots():
    # Monday timetable has 1 class from 10:00 to 11:30
    slots = [
        {"day_of_week": "Mon", "start_time": "10:00", "end_time": "11:30"}
    ]
    dates = [datetime.date(2026, 11, 16)]  # Monday
    free = get_free_slots(slots, dates)

    assert len(free) > 0
    # Candidate morning window was 07:00 to 13:00.
    # Minus 10:00-11:30 leaves 07:00-10:00 and 11:30-13:00
    times = [(f['start_time'], f['end_time']) for f in free]
    assert ("07:00", "10:00") in times
    assert ("11:30", "13:00") in times
    assert ("14:00", "23:00") in times


def test_build_schedule_basic():
    topics = [
        {"topic_id": 1, "topic_name": "Trees", "subject_name": "DSA", "estimated_hours": 3.0, "priority": 5, "difficulty_level": 5, "exam_date": "2026-11-20"},
        {"topic_id": 2, "topic_name": "Grammar", "subject_name": "English", "estimated_hours": 2.0, "priority": 1, "difficulty_level": 1, "exam_date": "2026-11-25"}
    ]
    # Free slots over 2 days
    free_slots = [
        {"date": "2026-11-17", "day_of_week": "Tue", "start_time": "09:00", "end_time": "12:00", "start_min": 540, "end_min": 720, "duration_hours": 3.0},
        {"date": "2026-11-18", "day_of_week": "Wed", "start_time": "09:00", "end_time": "12:00", "start_min": 540, "end_min": 720, "duration_hours": 3.0}
    ]

    res = build_schedule(topics, free_slots, reference_date="2026-11-16")
    sessions = res["sessions"]
    assert len(sessions) > 0

    # Highest urgency topic (Trees) must be scheduled first
    first_sess = sessions[0]
    assert first_sess["topic_id"] == 1
    assert first_sess["status"] == "planned"


def test_build_schedule_flags_insufficient_slots():
    topics = [
        {"topic_id": 1, "topic_name": "Huge Topic", "subject_name": "Physics", "estimated_hours": 10.0, "priority": 5, "difficulty_level": 5, "exam_date": "2026-11-17"}
    ]
    # Only 1 free slot of 2 hours before exam
    free_slots = [
        {"date": "2026-11-16", "day_of_week": "Mon", "start_time": "10:00", "end_time": "12:00", "start_min": 600, "end_min": 720, "duration_hours": 2.0}
    ]

    res = build_schedule(topics, free_slots, reference_date="2026-11-15")
    unscheduled = res["unscheduled_topics"]
    assert len(unscheduled) == 1
    assert unscheduled[0]["topic_id"] == 1
    assert unscheduled[0]["unallocated_hours"] == 8.0
    assert "Insufficient free slots" in unscheduled[0]["reason"]


def test_reflow_on_missed():
    conn = get_connection(":memory:")
    init_db(conn)
    seed_database(conn)

    # Get initial sessions
    sessions = queries.get_all_study_sessions(conn)
    planned = [s for s in sessions if s['status'] == 'planned']
    assert len(planned) > 0

    target_session = planned[0]
    session_id = target_session['session_id']

    # Trigger reflow on missed
    result = reflow_on_missed(session_id, conn)
    assert result['success'] is True
    assert result['missed_session_id'] == session_id

    # Check that session is now 'missed'
    updated = queries.get_study_session_by_id(conn, session_id)
    assert updated['status'] == 'missed'

    # Check that new planned sessions were created
    new_sessions = queries.get_all_study_sessions(conn)
    new_planned = [s for s in new_sessions if s['status'] == 'planned']
    assert len(new_planned) > 0
    conn.close()

