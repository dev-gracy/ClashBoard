"""
Study Scheduler Service for ClashBoard.
Layer: services/ — pure functions, zero GUI/Tkinter imports.

Day Order–aware free-slot extraction + urgency-based greedy allocation.
"""
import datetime
from services.clash_detector import time_to_minutes, minutes_to_time, ranges_overlap
from services.day_order import get_day_order


# ─────────────────────────────────────────────────────────────────────────────
# Core formulae
# ─────────────────────────────────────────────────────────────────────────────

def compute_urgency(priority: int, difficulty_level: int, days_until_exam: int) -> float:
    """Urgency = (priority × difficulty) / max(days_until_exam, 1)."""
    p = max(1, min(5, int(priority)))
    d = max(1, min(5, int(difficulty_level)))
    return (p * d) / max(int(days_until_exam), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Interval subtraction helper
# ─────────────────────────────────────────────────────────────────────────────

def _subtract_intervals(source, busy):
    """Remove all busy [start_min, end_min) intervals from source intervals."""
    result = list(source)
    for b_s, b_e in busy:
        new = []
        for s_s, s_e in result:
            if b_e <= s_s or b_s >= s_e:
                new.append((s_s, s_e))
            else:
                if b_s > s_s:
                    new.append((s_s, b_s))
                if b_e < s_e:
                    new.append((b_e, s_e))
        result = new
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Free slot extraction  (Day Order–aware)
# ─────────────────────────────────────────────────────────────────────────────

def get_free_slots(timetable_entries, date_range, exams=None,
                   pivot_date: str = None, pivot_day_order: int = 1,
                   min_slot_minutes: int = 30):
    """
    For each date in date_range:
      1. Determine its Day Order (skip weekends).
      2. Collect busy intervals from timetable slots for that Day Order.
      3. Subtract those + any exams scheduled on that exact date.
      4. Remaining windows inside the active study band (07:00–13:00 and 14:00–23:00)
         minus a 9-hr sleep/meal buffer form the free slots.

    Returns a list of dicts with keys:
      date, day_of_week, day_order, start_time, end_time, start_min, end_min, duration_hours
    """
    exams = exams or []
    if pivot_date is None:
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        pivot_date = monday.strftime('%Y-%m-%d')

    # Candidate study windows (minutes from midnight):
    #   07:00–13:00  and  14:00–23:00  (lunch break 13:00–14:00, sleep 23:00–07:00)
    base_windows = [(420, 780), (840, 1380)]

    # Build lookup: day_order → list of (start_min, end_min)
    timetable_by_do: dict[int, list] = {}
    for entry in timetable_entries:
        do = int(entry.get('day_order', 0))
        if not do:
            continue
        s_m = time_to_minutes(entry['start_time'])
        e_m = time_to_minutes(entry['end_time'])
        if e_m > s_m:
            timetable_by_do.setdefault(do, []).append((s_m, e_m))

    # Build exam lookup: date_str → list of (start_min, end_min)
    exam_by_date: dict[str, list] = {}
    for ex in exams:
        edate = ex.get('exam_date')
        if edate:
            s_m = time_to_minutes(ex['start_time'])
            e_m = time_to_minutes(ex['end_time'])
            if e_m > s_m:
                exam_by_date.setdefault(edate, []).append((s_m, e_m))

    free_slots = []
    day_names  = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    for d in date_range:
        if isinstance(d, datetime.datetime):
            d = d.date()
        date_str  = d.strftime('%Y-%m-%d')
        day_name  = day_names[d.weekday()]
        day_order = get_day_order(d, pivot_date, pivot_day_order)

        if day_order is None:
            continue   # weekend — skip

        busy = list(timetable_by_do.get(day_order, []))
        busy.extend(exam_by_date.get(date_str, []))

        remaining = _subtract_intervals(base_windows, busy)

        for s_m, e_m in sorted(remaining):
            dur_min = e_m - s_m
            if dur_min >= min_slot_minutes:
                free_slots.append({
                    'date'          : date_str,
                    'day_of_week'   : day_name,
                    'day_order'     : day_order,
                    'start_time'    : minutes_to_time(s_m),
                    'end_time'      : minutes_to_time(e_m),
                    'start_min'     : s_m,
                    'end_min'       : e_m,
                    'duration_hours': round(dur_min / 60.0, 2),
                })

    return free_slots


# ─────────────────────────────────────────────────────────────────────────────
# Greedy schedule builder
# ─────────────────────────────────────────────────────────────────────────────

def build_schedule(topics, free_slots, max_session_hours: float = 2.0,
                   reference_date=None):
    """
    Sort topics by urgency descending, then greedily allocate study slots.

    Returns:
      { 'sessions': [...], 'unscheduled_topics': [...] }
    """
    if reference_date is None:
        ref_dt = datetime.date.today()
    elif isinstance(reference_date, str):
        ref_dt = datetime.date.fromisoformat(reference_date)
    else:
        ref_dt = reference_date

    # Build working copy with urgency
    working = []
    for t in topics:
        exam_date_str = t.get('exam_date')
        days_until = 30
        if exam_date_str:
            try:
                ex_dt = datetime.date.fromisoformat(exam_date_str)
                days_until = max(0, (ex_dt - ref_dt).days)
            except Exception:
                pass

        working.append({
            'topic_id'      : t['topic_id'],
            'subject_id'    : t.get('subject_id'),
            'topic_name'    : t['topic_name'],
            'subject_name'  : t.get('subject_name', ''),
            'subject_code'  : t.get('subject_code', ''),
            'priority'      : t.get('priority', 3),
            'difficulty_level': t.get('difficulty_level', 3),
            'exam_date'     : exam_date_str,
            'days_until_exam': days_until,
            'urgency'       : compute_urgency(
                                  t.get('priority', 3),
                                  t.get('difficulty_level', 3),
                                  days_until),
            'remaining_hours': float(t.get('estimated_hours', 1.0)),
        })

    working.sort(key=lambda x: x['urgency'], reverse=True)

    # Mutable slot pool
    slot_pool = [
        {'date': s['date'], 'start_min': s['start_min'], 'end_min': s['end_min']}
        for s in free_slots
    ]

    max_chunk_min = int(max_session_hours * 60)
    min_chunk_min = 30
    sessions = []

    for topic in working:
        rem_min    = int(round(topic['remaining_hours'] * 60))
        exam_date  = topic.get('exam_date')

        for slot in slot_pool:
            if rem_min <= 0:
                break
            if exam_date and slot['date'] > exam_date:
                continue

            avail = slot['end_min'] - slot['start_min']
            if avail < min_chunk_min:
                continue

            alloc = min(rem_min, avail, max_chunk_min)
            leftover = avail - alloc
            # Don't leave an unusable splinter
            if 0 < leftover < min_chunk_min and rem_min >= alloc + leftover:
                alloc += leftover

            sess_start = slot['start_min']
            sess_end   = sess_start + alloc

            sessions.append({
                'topic_id'      : topic['topic_id'],
                'topic_name'    : topic['topic_name'],
                'subject_id'    : topic.get('subject_id'),
                'subject_name'  : topic.get('subject_name', ''),
                'subject_code'  : topic.get('subject_code', ''),
                'scheduled_date': slot['date'],
                'scheduled_start': minutes_to_time(sess_start),
                'scheduled_end'  : minutes_to_time(sess_end),
                'duration_hours': round(alloc / 60.0, 2),
                'status'        : 'planned',
            })

            rem_min -= alloc
            slot['start_min'] = sess_end

        topic['remaining_hours'] = max(0.0, round(rem_min / 60.0, 2))

    unscheduled = [
        {
            'topic_id'       : t['topic_id'],
            'topic_name'     : t['topic_name'],
            'subject_name'   : t['subject_name'],
            'unallocated_hours': t['remaining_hours'],
            'exam_date'      : t['exam_date'],
            'reason'         : (
                f"Not enough free slots before {t['exam_date']}"
                if t['exam_date'] else "Planning window exhausted"
            ),
        }
        for t in working if t['remaining_hours'] > 0
    ]

    return {'sessions': sessions, 'unscheduled_topics': unscheduled}


# ─────────────────────────────────────────────────────────────────────────────
# Adaptive missed-session reflow
# ─────────────────────────────────────────────────────────────────────────────

def reflow_on_missed(session_id, conn):
    """
    Mark session as 'missed', then recompute and reflow all future planned sessions.
    """
    from db import queries

    session = queries.get_study_session_by_id(conn, session_id)
    if not session:
        return {'success': False, 'error': f"Session {session_id} not found."}

    queries.update_study_session_status(conn, session_id, 'missed')

    today     = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')

    # Clear all future planned sessions
    queries.clear_planned_study_sessions(conn, from_date=today_str)

    # Compute remaining hours per topic (estimated - done)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic_id,
               SUM((strftime('%s','2000-01-01 '||scheduled_end) -
                    strftime('%s','2000-01-01 '||scheduled_start)) / 3600.0) AS done_hrs
        FROM StudySessions WHERE status='done' GROUP BY topic_id
    """)
    done_map = {row['topic_id']: (row['done_hrs'] or 0.0) for row in cursor.fetchall()}

    topics_to_schedule = []
    for t in queries.get_all_topics(conn):
        rem = max(0.0, round(float(t['estimated_hours']) - done_map.get(t['topic_id'], 0.0), 2))
        if rem > 0:
            t_copy = dict(t)
            t_copy['estimated_hours'] = rem
            topics_to_schedule.append(t_copy)

    # Load pivot settings
    pivot_date = queries.get_setting(conn, 'pivot_date')
    pivot_do   = int(queries.get_setting(conn, 'pivot_day_order', '1'))

    timetable_slots = queries.get_all_timetable_slots(conn)
    exams           = queries.get_all_exams(conn)
    planning_days   = [today + datetime.timedelta(days=i) for i in range(21)]
    free_slots      = get_free_slots(timetable_slots, planning_days, exams, pivot_date, pivot_do)

    plan = build_schedule(topics_to_schedule, free_slots, reference_date=today)

    with conn:
        for s in plan['sessions']:
            queries.insert_study_session(
                conn,
                topic_id        = s['topic_id'],
                scheduled_date  = s['scheduled_date'],
                scheduled_start = s['scheduled_start'],
                scheduled_end   = s['scheduled_end'],
                status          = 'planned',
            )

    return {
        'success'               : True,
        'missed_session_id'     : session_id,
        'reflowed_sessions_count': len(plan['sessions']),
        'unscheduled_topics'    : plan['unscheduled_topics'],
    }
