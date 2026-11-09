"""
Services package for ClashBoard.
Layer: services/ (pure functions, zero Tkinter imports, unit-testable standalone).
"""
from services.clash_detector import ranges_overlap, detect_clashes, time_to_minutes, minutes_to_time
from services.scheduler import compute_urgency, get_free_slots, build_schedule, reflow_on_missed

__all__ = [
    "ranges_overlap",
    "detect_clashes",
    "time_to_minutes",
    "minutes_to_time",
    "compute_urgency",
    "get_free_slots",
    "build_schedule",
    "reflow_on_missed"
]

