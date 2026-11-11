"""
Unit tests for Clash Detection service — updated for Day Order schema.
"""
import datetime
import pytest
from services.clash_detector import ranges_overlap, detect_clashes, time_to_minutes, minutes_to_time


def test_time_conversions():
    assert time_to_minutes("00:00") == 0
    assert time_to_minutes("10:30") == 630
    assert time_to_minutes("23:59") == 1439
    assert minutes_to_time(630) == "10:30"
    assert minutes_to_time(0) == "00:00"


def test_ranges_overlap():
    assert not ranges_overlap("09:00", "10:00", "10:00", "11:00")
    assert not ranges_overlap("08:00", "09:00", "14:00", "15:00")
    assert ranges_overlap("10:00", "11:30", "11:00", "12:00")
    assert ranges_overlap("10:00", "14:00", "11:00", "12:00")
    assert ranges_overlap("10:00", "11:00", "10:00", "11:00")


def test_detect_class_class_clash():
    # Two slots on Day Order 1 that overlap
    slots = [
        {"slot_id": 1, "subject_name": "Math",      "day_order": 1, "start_time": "10:00", "end_time": "11:30", "section": "A"},
        {"slot_id": 2, "subject_name": "Physics",   "day_order": 1, "start_time": "11:00", "end_time": "12:30", "section": "B"},
        {"slot_id": 3, "subject_name": "Chemistry", "day_order": 2, "start_time": "10:00", "end_time": "11:30", "section": "C"},
    ]
    clashes = detect_clashes(slots, exams=[])
    assert len(clashes) == 1
    assert clashes[0]["clash_type"] == "class-class"
    assert clashes[0]["slot_id_1"] == 1
    assert clashes[0]["slot_id_2"] == 2


def test_detect_exam_exam_clash():
    exams = [
        {"exam_id": 10, "subject_name": "DS",  "exam_date": "2026-11-20", "start_time": "14:00", "end_time": "16:00"},
        {"exam_id": 11, "subject_name": "T&T", "exam_date": "2026-11-20", "start_time": "15:00", "end_time": "17:00"},
        {"exam_id": 12, "subject_name": "OS",  "exam_date": "2026-11-21", "start_time": "14:00", "end_time": "16:00"},
    ]
    clashes = detect_clashes(timetable_entries=[], exams=exams)
    assert len(clashes) == 1
    assert clashes[0]["clash_type"] == "exam-exam"


def test_detect_class_exam_clash():
    # Pivot: 2026-11-16 (Monday) = Day Order 1
    # Day Order 1 has a class 10:00-11:30
    # Exam on 2026-11-16 (a Monday → Day Order 1) overlaps
    pivot_date = "2026-11-16"
    pivot_do   = 1

    slots = [
        {"slot_id": 1, "subject_name": "DAA", "day_order": 1,
         "start_time": "10:00", "end_time": "11:30", "section": "Sec 1"}
    ]
    exams = [
        {"exam_id": 5, "subject_name": "Physics", "exam_date": "2026-11-16",
         "start_time": "11:00", "end_time": "13:00"}
    ]
    clashes = detect_clashes(slots, exams, pivot_date, pivot_do)
    assert len(clashes) == 1
    assert clashes[0]["clash_type"] == "class-exam"
    assert clashes[0]["slot_id_1"] == 1
    assert clashes[0]["exam_id"]   == 5
