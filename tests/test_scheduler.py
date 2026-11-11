"""
Unit tests for Study Scheduler service — updated for Day Order schema.
"""
import datetime
import pytest
from services.scheduler import compute_urgency, get_free_slots, build_schedule, reflow_on_missed
from db.connection import get_connection
from db.schema import init_db
from db.seed import seed_database
from db import queries


def test_compute_urgency():
    assert compute_urgency(5, 5, 5) == 5.0
    assert compute_urgency(4, 3, 1) == 12.0
    assert compute_urgency(4, 4, 0) == 16.0   # max(0,1) → 1
    assert compute_urgency(1, 1, 10) < compute_urgency(5, 5, 10)


def test_get_free_slots():
    # Day Order 1 has a class 10:00–11:30
    # 2026-11-16 is a Monday; use pivot 2026-11-16 = Day Order 1
    slots = [
        {"day_order": 1, "start_time": "10:00", "end_time": "11:30"}
    ]
    pivot_date = "2026-11-16"
    pivot_do   = 1
    dates = [datetime.date(2026, 11, 16)]   # Monday → DO1

    free = get_free_slots(slots, dates, pivot_date=pivot_date, pivot_day_order=pivot_do)
    assert len(free) > 0

    times = [(f['start_time'], f['end_time']) for f in free]
    # 07:00–10:00 and 11:30–13:00 and 14:00–23:00 should all exist
    assert ("07:00", "10:00") in times
    assert ("11:30", "13:00") in times
    assert ("14:00", "23:00") in times


def test_build_schedule_basic():
    topics = [
        {"topic_id": 1, "topic_name": "Trees", "subject_name": "DS",
         "estimated_hours": 3.0, "priority": 5, "difficulty_level": 5, "exam_date": "2026-11-20"},
        {"topic_id": 2, "topic_name": "Grammar", "subject_name": "English",
         "estimated_hours": 2.0, "priority": 1, "difficulty_level": 1, "exam_date": "2026-11-25"},
    ]
    free_slots = [
        {"date": "2026-11-17", "day_of_week": "Tue", "day_order": 2,
         "start_time": "09:00", "end_time": "12:00", "start_min": 540, "end_min": 720, "duration_hours": 3.0},
        {"date": "2026-11-18", "day_of_week": "Wed", "day_order": 3,
         "start_time": "09:00", "end_time": "12:00", "start_min": 540, "end_min": 720, "duration_hours": 3.0},
    ]
    res = build_schedule(topics, free_slots, reference_date="2026-11-16")
    assert len(res["sessions"]) > 0
    # Highest urgency topic (Trees) must come first
    assert res["sessions"][0]["topic_id"] == 1
    assert res["sessions"][0]["status"] == "planned"


def test_build_schedule_flags_insufficient_slots():
    topics = [
        {"topic_id": 1, "topic_name": "Huge Topic", "subject_name": "Physics",
         "estimated_hours": 10.0, "priority": 5, "difficulty_level": 5, "exam_date": "2026-11-17"},
    ]
    free_slots = [
        {"date": "2026-11-16", "day_of_week": "Mon", "day_order": 1,
         "start_time": "10:00", "end_time": "12:00", "start_min": 600, "end_min": 720, "duration_hours": 2.0},
    ]
    res = build_schedule(topics, free_slots, reference_date="2026-11-15")
    unscheduled = res["unscheduled_topics"]
    assert len(unscheduled) == 1
    assert unscheduled[0]["topic_id"] == 1
    assert unscheduled[0]["unallocated_hours"] == 8.0
    # Reason mentions exam date
    assert "2026-11-17" in unscheduled[0]["reason"]


def test_reflow_on_missed():
    conn = get_connection(":memory:")
    init_db(conn)
    seed_database(conn)

    sessions = queries.get_all_study_sessions(conn)
    planned  = [s for s in sessions if s['status'] == 'planned']
    assert len(planned) > 0

    sid    = planned[0]['session_id']
    result = reflow_on_missed(sid, conn)

    assert result['success'] is True
    assert result['missed_session_id'] == sid

    updated = queries.get_study_session_by_id(conn, sid)
    assert updated['status'] == 'missed'

    new_planned = [s for s in queries.get_all_study_sessions(conn) if s['status'] == 'planned']
    assert len(new_planned) > 0
    conn.close()
