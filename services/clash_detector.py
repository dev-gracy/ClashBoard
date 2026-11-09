"""
Clash Detection Service for ClashBoard.
Layer: services/ (pure functions, zero GUI/Tkinter imports, unit-testable).

Detects three types of scheduling conflicts:
1. class-class: Two timetable classes on the same day overlap in time.
2. class-exam: A regular timetable class on a given weekday overlaps with an exam scheduled on that calendar date.
3. exam-exam: Two exams scheduled on the same calendar date overlap in time.
"""
import datetime


def time_to_minutes(time_str):
    """Converts 'HH:MM' string to minutes from 00:00."""
    try:
        parts = time_str.strip().split(':')
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except Exception:
        return 0


def minutes_to_time(minutes):
    """Converts integer minutes to 'HH:MM' string."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def ranges_overlap(start_a, end_a, start_b, end_b):
    """
    Determines if two time ranges overlap.
    Handles 'HH:MM' 24-hr string inputs or integer minute inputs.
    Standard definition: start_a < end_b and start_b < end_a.
    """
    if isinstance(start_a, str):
        # In 24-hr 'HH:MM' format, string comparison works identically to minutes
        # unless an interval wraps midnight.
        min_sa = time_to_minutes(start_a)
        min_ea = time_to_minutes(end_a)
        min_sb = time_to_minutes(start_b)
        min_eb = time_to_minutes(end_b)

        # Handle midnight wrap (e.g. 23:00 to 01:00)
        if min_ea <= min_sa:
            min_ea += 24 * 60
        if min_eb <= min_sb:
            min_eb += 24 * 60

        return min_sa < min_eb and min_sb < min_ea
    else:
        return start_a < end_b and start_b < end_a


def get_weekday_from_date(date_str):
    """
    Converts 'YYYY-MM-DD' into three-letter weekday: 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'.
    """
    try:
        dt = datetime.date.fromisoformat(date_str)
        return dt.strftime('%a')
    except Exception:
        return ""


def detect_clashes(timetable_entries, exams):
    """
    Compare every same-day pair of timetable entries -> clash_type 'class-class'.
    Compare every timetable entry against exams on the same date -> 'class-exam'.
    Compare every pair of exams on the same date -> 'exam-exam'.
    Group entries by day/date first, then check ranges_overlap() pairwise within each group.
    
    Returns a list of dicts ready to insert into the Clashes table:
    [
        {
            'slot_id_1': int or None,
            'slot_id_2': int or None,
            'exam_id': int or None,
            'clash_type': 'class-class' | 'class-exam' | 'exam-exam',
            'detected_on': 'YYYY-MM-DD HH:MM:SS',
            'description': '...'
        },
        ...
    ]
    """
    clashes = []
    now_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. CLASS-CLASS CLASHES
    # Group timetable entries by day_of_week
    classes_by_day = {}
    for entry in timetable_entries:
        day = entry.get('day_of_week', '').capitalize()[:3]
        if day:
            classes_by_day.setdefault(day, []).append(entry)

    for day, entries in classes_by_day.items():
        n = len(entries)
        for i in range(n):
            for j in range(i + 1, n):
                a = entries[i]
                b = entries[j]
                if ranges_overlap(a['start_time'], a['end_time'], b['start_time'], b['end_time']):
                    sub_a = a.get('subject_name') or a.get('subject_code') or f"Class #{a.get('slot_id')}"
                    sec_a = f" ({a['section']})" if a.get('section') else ""
                    sub_b = b.get('subject_name') or b.get('subject_code') or f"Class #{b.get('slot_id')}"
                    sec_b = f" ({b['section']})" if b.get('section') else ""
                    
                    desc = (
                        f"{sub_a}{sec_a} [{a['start_time']}-{a['end_time']}] overlaps with "
                        f"{sub_b}{sec_b} [{b['start_time']}-{b['end_time']}] on {day}"
                    )
                    clashes.append({
                        'slot_id_1': a.get('slot_id'),
                        'slot_id_2': b.get('slot_id'),
                        'exam_id': None,
                        'clash_type': 'class-class',
                        'detected_on': now_ts,
                        'description': desc
                    })

    # 2. EXAM-EXAM CLASHES
    # Group exams by exam_date
    exams_by_date = {}
    for exam in exams:
        edate = exam.get('exam_date')
        if edate:
            exams_by_date.setdefault(edate, []).append(exam)

    for edate, ex_list in exams_by_date.items():
        n = len(ex_list)
        for i in range(n):
            for j in range(i + 1, n):
                ex_a = ex_list[i]
                ex_b = ex_list[j]
                if ranges_overlap(ex_a['start_time'], ex_a['end_time'], ex_b['start_time'], ex_b['end_time']):
                    sub_a = ex_a.get('subject_name') or ex_a.get('subject_code') or f"Exam #{ex_a.get('exam_id')}"
                    sub_b = ex_b.get('subject_name') or ex_b.get('subject_code') or f"Exam #{ex_b.get('exam_id')}"
                    desc = (
                        f"{sub_a} exam [{ex_a['start_time']}-{ex_a['end_time']}] overlaps with "
                        f"{sub_b} exam [{ex_b['start_time']}-{ex_b['end_time']}] on {edate}"
                    )
                    clashes.append({
                        'slot_id_1': None,
                        'slot_id_2': None,
                        'exam_id': ex_a.get('exam_id'),
                        'clash_type': 'exam-exam',
                        'detected_on': now_ts,
                        'description': desc
                    })

    # 3. CLASS-EXAM CLASHES
    # For every exam, find which weekday it falls on, then compare against classes on that weekday
    for exam in exams:
        edate = exam.get('exam_date')
        if not edate:
            continue
        weekday = get_weekday_from_date(edate)
        classes_on_day = classes_by_day.get(weekday, [])
        for cls in classes_on_day:
            if ranges_overlap(cls['start_time'], cls['end_time'], exam['start_time'], exam['end_time']):
                cls_sub = cls.get('subject_name') or cls.get('subject_code') or f"Class #{cls.get('slot_id')}"
                cls_sec = f" ({cls['section']})" if cls.get('section') else ""
                ex_sub = exam.get('subject_name') or exam.get('subject_code') or f"Exam #{exam.get('exam_id')}"
                desc = (
                    f"{cls_sub}{cls_sec} class [{cls['start_time']}-{cls['end_time']}] overlaps with "
                    f"{ex_sub} exam [{exam['start_time']}-{exam['end_time']}] on {edate} ({weekday})"
                )
                clashes.append({
                    'slot_id_1': cls.get('slot_id'),
                    'slot_id_2': None,
                    'exam_id': exam.get('exam_id'),
                    'clash_type': 'class-exam',
                    'detected_on': now_ts,
                    'description': desc
                })

    return clashes

