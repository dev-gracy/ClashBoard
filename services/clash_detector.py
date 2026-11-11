"""
Clash Detection Service for ClashBoard.
Layer: services/ — pure functions, zero GUI/Tkinter imports.

Three conflict types:
  class-class : Two Timetable slots on the same Day Order overlap in time.
  class-exam  : A recurring class (DO-based) collides with an exam on a calendar date
                whose Day Order matches.
  exam-exam   : Two exams on the same calendar date overlap in time.
"""
import datetime
from services.day_order import get_day_order


def time_to_minutes(time_str: str) -> int:
    """'HH:MM' → minutes from midnight."""
    try:
        h, m = time_str.strip().split(':')
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def minutes_to_time(minutes: int) -> str:
    """minutes from midnight → 'HH:MM'."""
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def ranges_overlap(start_a, end_a, start_b, end_b) -> bool:
    """
    Returns True if the two time intervals overlap (exclusive endpoints).
    Accepts 'HH:MM' strings or integer minutes.
    Handles midnight-crossing intervals.
    """
    if isinstance(start_a, str):
        sa, ea = time_to_minutes(start_a), time_to_minutes(end_a)
        sb, eb = time_to_minutes(start_b), time_to_minutes(end_b)
        if ea <= sa:
            ea += 24 * 60       # midnight wrap
        if eb <= sb:
            eb += 24 * 60
        return sa < eb and sb < ea
    return start_a < end_b and start_b < end_a


def detect_clashes(timetable_entries, exams, pivot_date: str = None, pivot_day_order: int = 1):
    """
    Detect all three types of scheduling conflicts.

    Parameters
    ----------
    timetable_entries : list[dict]  — rows from Timetable (each has 'day_order')
    exams             : list[dict]  — rows from Exams
    pivot_date        : str         — 'YYYY-MM-DD' anchor for Day Order calendar mapping
    pivot_day_order   : int         — Day Order (1–5) on pivot_date

    Returns a list of dicts ready to INSERT into the Clashes table.
    """
    if pivot_date is None:
        today   = datetime.date.today()
        monday  = today - datetime.timedelta(days=today.weekday())
        pivot_date       = monday.strftime('%Y-%m-%d')
        pivot_day_order  = 1

    clashes  = []
    now_ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Group timetable entries by day_order
    classes_by_do: dict[int, list] = {}
    for entry in timetable_entries:
        do = int(entry.get('day_order', 0))
        if do:
            classes_by_do.setdefault(do, []).append(entry)

    # ── 1. class-class  (same Day Order, same timetable) ────────────────────
    for do, entries in classes_by_do.items():
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                a, b = entries[i], entries[j]
                if ranges_overlap(a['start_time'], a['end_time'],
                                  b['start_time'], b['end_time']):
                    sub_a = a.get('subject_name') or a.get('subject_code', f"Slot#{a.get('slot_id')}")
                    sub_b = b.get('subject_name') or b.get('subject_code', f"Slot#{b.get('slot_id')}")
                    room_a = f" [{a['section']}]" if a.get('section') else ""
                    room_b = f" [{b['section']}]" if b.get('section') else ""
                    desc = (
                        f"Day Order {do}: {sub_a}{room_a} "
                        f"[{a['start_time']}–{a['end_time']}] overlaps with "
                        f"{sub_b}{room_b} [{b['start_time']}–{b['end_time']}]"
                    )
                    clashes.append({
                        'slot_id_1': a.get('slot_id'),
                        'slot_id_2': b.get('slot_id'),
                        'exam_id'  : None,
                        'clash_type': 'class-class',
                        'detected_on': now_ts,
                        'description': desc,
                    })

    # Group exams by exam_date
    exams_by_date: dict[str, list] = {}
    for ex in exams:
        edate = ex.get('exam_date')
        if edate:
            exams_by_date.setdefault(edate, []).append(ex)

    # ── 2. exam-exam  (same calendar date) ──────────────────────────────────
    for edate, ex_list in exams_by_date.items():
        for i in range(len(ex_list)):
            for j in range(i + 1, len(ex_list)):
                a, b = ex_list[i], ex_list[j]
                if ranges_overlap(a['start_time'], a['end_time'],
                                  b['start_time'], b['end_time']):
                    sub_a = a.get('subject_name') or a.get('subject_code', f"Exam#{a.get('exam_id')}")
                    sub_b = b.get('subject_name') or b.get('subject_code', f"Exam#{b.get('exam_id')}")
                    desc = (
                        f"{sub_a} exam [{a['start_time']}–{a['end_time']}] overlaps with "
                        f"{sub_b} exam [{b['start_time']}–{b['end_time']}] on {edate}"
                    )
                    clashes.append({
                        'slot_id_1': None,
                        'slot_id_2': None,
                        'exam_id'  : a.get('exam_id'),
                        'clash_type': 'exam-exam',
                        'detected_on': now_ts,
                        'description': desc,
                    })

    # ── 3. class-exam  (Day Order of exam date matches a timetable Day Order) ─
    for exam in exams:
        edate = exam.get('exam_date')
        if not edate:
            continue
        try:
            exam_dt = datetime.date.fromisoformat(edate)
        except ValueError:
            continue

        exam_do = get_day_order(exam_dt, pivot_date, pivot_day_order)
        if exam_do is None:
            continue   # exam on a weekend, can't collide with weekday classes

        classes_on_do = classes_by_do.get(exam_do, [])
        for cls in classes_on_do:
            if ranges_overlap(cls['start_time'], cls['end_time'],
                              exam['start_time'], exam['end_time']):
                cls_sub  = cls.get('subject_name')  or cls.get('subject_code',  f"Slot#{cls.get('slot_id')}")
                ex_sub   = exam.get('subject_name') or exam.get('subject_code', f"Exam#{exam.get('exam_id')}")
                room_cls = f" [{cls['section']}]" if cls.get('section') else ""
                desc = (
                    f"{cls_sub}{room_cls} class [{cls['start_time']}–{cls['end_time']}] (Day Order {exam_do}) "
                    f"overlaps with {ex_sub} exam [{exam['start_time']}–{exam['end_time']}] "
                    f"on {edate}"
                )
                clashes.append({
                    'slot_id_1': cls.get('slot_id'),
                    'slot_id_2': None,
                    'exam_id'  : exam.get('exam_id'),
                    'clash_type': 'class-exam',
                    'detected_on': now_ts,
                    'description': desc,
                })

    return clashes
