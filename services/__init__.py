"""
Services package for ClashBoard.
Pure functions — zero Tkinter imports.
"""
from services.clash_detector import ranges_overlap, detect_clashes, time_to_minutes, minutes_to_time
from services.scheduler import compute_urgency, get_free_slots, build_schedule, reflow_on_missed
from services.day_order import (
    get_day_order, count_working_days_between,
    get_dates_for_day_order_in_week, week_monday, day_order_label,
    DAY_ORDER_LABELS,
)

__all__ = [
    "ranges_overlap", "detect_clashes", "time_to_minutes", "minutes_to_time",
    "compute_urgency", "get_free_slots", "build_schedule", "reflow_on_missed",
    "get_day_order", "count_working_days_between", "get_dates_for_day_order_in_week",
    "week_monday", "day_order_label", "DAY_ORDER_LABELS",
]
