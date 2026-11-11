"""
Day Order calculation utilities for ClashBoard.
Day Order (DO) cycles 1→5 on working days (Mon–Fri), skipping weekends.
A pivot date + pivot_do anchor the entire calendar-to-day-order mapping.
"""
import datetime

DAY_ORDER_LABELS = {
    1: "Day 1",
    2: "Day 2",
    3: "Day 3",
    4: "Day 4",
    5: "Day 5",
}

DAYS_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


def count_working_days_between(start: datetime.date, end: datetime.date) -> int:
    """
    Count Mon–Fri working days from `start` up to (but not including) `end`.
    Returns positive when end > start, negative when end < start.
    """
    if start == end:
        return 0
    sign = 1 if end > start else -1
    count = 0
    current = start
    while current != end:
        if current.weekday() < 5:        # Mon=0 … Fri=4
            count += sign
        current += datetime.timedelta(days=sign)
    return count


def get_day_order(date: datetime.date, pivot_date_str: str, pivot_do: int):
    """
    Returns the Day Order (1–5) for a given calendar date, or None for weekends.

    Parameters
    ----------
    date : datetime.date
    pivot_date_str : str  'YYYY-MM-DD' — a working day with a known Day Order
    pivot_do : int        1–5, the Day Order on pivot_date
    """
    if date.weekday() >= 5:   # Sat or Sun
        return None
    pivot = datetime.date.fromisoformat(pivot_date_str)
    working_days = count_working_days_between(pivot, date)
    return ((pivot_do - 1 + working_days) % 5) + 1


def get_dates_for_day_order_in_week(day_order: int, week_monday: datetime.date,
                                    pivot_date_str: str, pivot_do: int):
    """
    Returns the calendar date (or None) within a 7-day week starting on `week_monday`
    that corresponds to the given `day_order`.
    """
    for i in range(5):          # Mon–Fri only
        d = week_monday + datetime.timedelta(days=i)
        if get_day_order(d, pivot_date_str, pivot_do) == day_order:
            return d
    return None


def week_monday(date: datetime.date) -> datetime.date:
    """Returns the Monday of the week containing `date`."""
    return date - datetime.timedelta(days=date.weekday())


def day_order_label(do: int | None) -> str:
    """Human-readable label, e.g. 'Day 3' or '' for weekends/None."""
    return DAY_ORDER_LABELS.get(do, "")

