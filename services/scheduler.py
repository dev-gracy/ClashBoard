"""
Study Scheduler Service for ClashBoard.
Layer: services/ (pure functions, zero GUI/Tkinter imports, unit-testable).

Implements:
1. compute_urgency(priority, difficulty_level, days_until_exam)
2. get_free_slots(timetable_entries, date_range, exams)
3. build_schedule(topics, free_slots, max_session_hours, reference_date)
4. reflow_on_missed(session_id, conn)
"""
import datetime
from services.clash_detector import time_to_minutes, minutes_to_time, ranges_overlap, get_weekday_from_date


def compute_urgency(priority, difficulty_level, days_until_exam):
    """
    Urgency formula: (priority * difficulty_level) / max(days_until_exam, 1)
    priority: 1 to 5
    difficulty_level: 1 to 5
    days_until_exam: integer >= 0
    """
    p = max(1, min(5, int(priority)))
    d = max(1, min(5, int(difficulty_level)))
    days = max(1, int(days_until_exam))
    return (p * d) / days


def subtract_intervals(source_intervals, busy_intervals):
    """
    Subtract busy [start, end] intervals (in minutes) from a list of source intervals.
    Returns remaining disjoint intervals.
    """
    result = source_intervals[:]
    for b_start, b_end in busy_intervals:
        new_result = []
        for s_start, s_end in result:
            # Case 1: No overlap
            if b_end <= s_start or b_start >= s_end:
                new_result.append((s_start, s_end))
            else:
                # Case 2: Busy overlaps start
                if b_start > s_start:
                    new_result.append((s_start, b_start))
                # Case 3: Busy overlaps end
                if b_end < s_end:
                    new_result.append((b_end, s_end))
        result = new_result
    return result


def get_free_slots(timetable_entries, date_range, exams=None, min_slot_minutes=30):
    """
    For each day in date_range: 24 hours minus that day's Timetable entries
    minus a fixed sleep/meals buffer (hardcode ~9 hours total).
    
    Sleep buffer: 23:00 to 07:00 (8 hours)
    Meal buffer: 13:00 to 14:00 (1 hour lunch)
    Total fixed buffer: 9 hours.
    Available awake/study candidate hours: 07:00 - 13:00 (6 hrs) and 14:00 - 23:00 (9 hrs).
    
    Returns a list of free time slot dicts:
    [
        {
            'date': 'YYYY-MM-DD',
            'day_of_week': 'Mon',
            'start_time': 'HH:MM',
            'end_time': 'HH:MM',
            'start_min': int,
            'end_min': int,
            'duration_hours': float
        },
        ...
    ]
    """
    exams = exams or []
    free_slots = []
    
    # Base candidate active intervals in minutes from midnight (total 15 hours = 24 - 9 buffer)
    # 07:00 (420) to 13:00 (780)
    # 14:00 (840) to 23:00 (1380)
    base_active_windows = [
        (420, 780),
        (840, 1380)
    ]

    for d in date_range:
        date_str = d.strftime("%Y-%m-%d") if isinstance(d, (datetime.date, datetime.datetime)) else str(d)
        weekday = get_weekday_from_date(date_str)

        # Collect busy intervals from timetable on this weekday
        busy_intervals = []
        for entry in timetable_entries:
            if entry.get('day_of_week', '').capitalize()[:3] == weekday:
                s_min = time_to_minutes(entry['start_time'])
                e_min = time_to_minutes(entry['end_time'])
                if e_min > s_min:
                    busy_intervals.append((s_min, e_min))

        # Collect busy intervals from exams on this specific date
        for ex in exams:
            if ex.get('exam_date') == date_str:
                s_min = time_to_minutes(ex['start_time'])
                e_min = time_to_minutes(ex['end_time'])
                if e_min > s_min:
                    busy_intervals.append((s_min, e_min))

        # Subtract all busy intervals from candidate active windows
        remaining = subtract_intervals(base_active_windows, busy_intervals)
        
        for s_min, e_min in sorted(remaining):
            dur_min = e_min - s_min
            if dur_min >= min_slot_minutes:
                free_slots.append({
                    'date': date_str,
                    'day_of_week': weekday,
                    'start_time': minutes_to_time(s_min),
                    'end_time': minutes_to_time(e_min),
                    'start_min': s_min,
                    'end_min': e_min,
                    'duration_hours': round(dur_min / 60.0, 2)
                })

    return free_slots


def build_schedule(topics, free_slots, max_session_hours=2.0, reference_date=None):
    """
    Sort topics by compute_urgency() descending.
    Walk free_slots in date order; for each topic, allocate its
    estimated_hours, splitting across multiple slots/days if one
    slot isn't enough, until every topic is scheduled or slots run out.
    Return a dict:
    {
        'sessions': list of StudySessions dicts (status='planned'),
        'unscheduled_topics': list of topic dicts that couldn't be fully scheduled before exam/slots
    }
    """
    if reference_date is None:
        ref_dt = datetime.date.today()
    elif isinstance(reference_date, str):
        ref_dt = datetime.date.fromisoformat(reference_date)
    else:
        ref_dt = reference_date

    # Deep copy topics and calculate urgency
    topics_working = []
    for t in topics:
        exam_date_str = t.get('exam_date')
        if exam_date_str:
            try:
                ex_dt = datetime.date.fromisoformat(exam_date_str)
                days_until = (ex_dt - ref_dt).days
                if days_until < 0:
                    # Exam already passed, lower priority or treat as 1
                    days_until = 1
            except Exception:
                days_until = 30
        else:
            days_until = 30  # Default horizon if no exam set

        urgency = compute_urgency(
            priority=t.get('priority', 3),
            difficulty_level=t.get('difficulty_level', 3),
            days_until_exam=days_until
        )

        topics_working.append({
            'topic_id': t['topic_id'],
            'subject_id': t.get('subject_id'),
            'topic_name': t['topic_name'],
            'subject_name': t.get('subject_name', ''),
            'subject_code': t.get('subject_code', ''),
            'priority': t.get('priority', 3),
            'difficulty_level': t.get('difficulty_level', 3),
            'exam_date': exam_date_str,
            'days_until_exam': days_until,
            'urgency': urgency,
            'remaining_hours': float(t.get('estimated_hours', 1.0))
        })

    # Sort topics descending by urgency
    topics_working.sort(key=lambda x: x['urgency'], reverse=True)

    # Work with a mutable copy of free slots
    # Each slot: {'date': ..., 'start_min': ..., 'end_min': ...}
    available_slots = []
    for slot in free_slots:
        available_slots.append({
            'date': slot['date'],
            'start_min': slot['start_min'],
            'end_min': slot['end_min']
        })

    sessions = []
    max_chunk_min = int(max_session_hours * 60)
    min_chunk_min = 30  # Don't schedule less than 30 min

    # Allocate topics
    for topic in topics_working:
        rem_min = int(round(topic['remaining_hours'] * 60))
        exam_date = topic.get('exam_date')

        for slot in available_slots:
            if rem_min <= 0:
                break
            
            # If topic has an exam date, cannot schedule after or on the exam day (or during/after exam)
            if exam_date and slot['date'] > exam_date:
                continue

            slot_avail = slot['end_min'] - slot['start_min']
            if slot_avail < min_chunk_min:
                continue

            # Allocate up to max_chunk_min or remaining needed minutes
            alloc_min = min(rem_min, slot_avail, max_chunk_min)

            # Check if this allocation leaves an unusable splinter < min_chunk_min
            leftover = slot_avail - alloc_min
            if 0 < leftover < min_chunk_min and (alloc_min + leftover <= slot_avail) and (rem_min >= alloc_min + leftover):
                alloc_min += leftover

            sess_start = slot['start_min']
            sess_end = sess_start + alloc_min

            sessions.append({
                'topic_id': topic['topic_id'],
                'topic_name': topic['topic_name'],
                'subject_id': topic.get('subject_id'),
                'subject_name': topic.get('subject_name', ''),
                'subject_code': topic.get('subject_code', ''),
                'scheduled_date': slot['date'],
                'scheduled_start': minutes_to_time(sess_start),
                'scheduled_end': minutes_to_time(sess_end),
                'duration_hours': round(alloc_min / 60.0, 2),
                'status': 'planned'
            })

            rem_min -= alloc_min
            slot['start_min'] = sess_end

        topic['remaining_hours'] = max(0.0, round(rem_min / 60.0, 2))

    # Identify any topics that could not be fully scheduled
    unscheduled = []
    for topic in topics_working:
        if topic['remaining_hours'] > 0:
            unscheduled.append({
                'topic_id': topic['topic_id'],
                'topic_name': topic['topic_name'],
                'subject_name': topic['subject_name'],
                'unallocated_hours': topic['remaining_hours'],
                'exam_date': topic['exam_date'],
                'reason': (
                    f"Insufficient free slots before exam date ({topic['exam_date']})"
                    if topic['exam_date'] else "All free slots exhausted in planning window"
                )
            })

    return {
        'sessions': sessions,
        'unscheduled_topics': unscheduled
    }


def reflow_on_missed(session_id, conn):
    """
    Mark the given session's status as 'missed'.
    Recompute urgency for its topic (same formula — days_until_exam
    has now shrunk, so urgency rises).
    Re-run build_schedule() over only the remaining free slots from
    today onward, and update StudySessions accordingly.
    This visibly changes the planner view when called.
    """
    from db import queries

    # 1. Fetch the target session
    session = queries.get_study_session_by_id(conn, session_id)
    if not session:
        return {'success': False, 'error': f"Session {session_id} not found."}

    # 2. Mark this session as 'missed'
    queries.update_study_session_status(conn, session_id, 'missed')

    # 3. Calculate remaining hours for each topic
    # Remaining hours = estimated_hours - completed ('done') hours
    today_dt = datetime.date.today()
    today_str = today_dt.strftime("%Y-%m-%d")

    # Clear all future 'planned' sessions from today onward
    # (Sessions that are 'done' or 'missed' remain intact in history)
    queries.clear_planned_study_sessions(conn, from_date=today_str)

    all_topics = queries.get_all_topics(conn)
    completed_hours_by_sub = queries.get_completed_hours_by_subject(conn)
    completed_map = {row['subject_id']: row['completed_hours'] for row in completed_hours_by_sub}

    # Compute done hours per topic
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic_id, 
               SUM((strftime('%s', '2000-01-01 ' || scheduled_end) - 
                    strftime('%s', '2000-01-01 ' || scheduled_start)) / 3600.0) AS done_hrs
        FROM StudySessions
        WHERE status = 'done'
        GROUP BY topic_id
    """)
    done_per_topic = {row['topic_id']: (row['done_hrs'] or 0.0) for row in cursor.fetchall()}

    topics_to_schedule = []
    for t in all_topics:
        done_hrs = done_per_topic.get(t['topic_id'], 0.0)
        rem_hrs = max(0.0, round(float(t['estimated_hours']) - done_hrs, 2))
        if rem_hrs > 0:
            t_copy = dict(t)
            t_copy['estimated_hours'] = rem_hrs
            topics_to_schedule.append(t_copy)

    # 4. Generate free slots for the next 21 days from today
    timetable_slots = queries.get_all_timetable_slots(conn)
    exams = queries.get_all_exams(conn)
    planning_days = [today_dt + datetime.timedelta(days=i) for i in range(21)]
    free_slots = get_free_slots(timetable_slots, planning_days, exams=exams)

    # 5. Re-run build_schedule
    plan_result = build_schedule(topics_to_schedule, free_slots, reference_date=today_dt)

    # 6. Insert new planned sessions into DB
    with conn:
        for s in plan_result['sessions']:
            queries.insert_study_session(
                conn,
                topic_id=s['topic_id'],
                scheduled_date=s['scheduled_date'],
                scheduled_start=s['scheduled_start'],
                scheduled_end=s['scheduled_end'],
                status='planned'
            )

    return {
        'success': True,
        'missed_session_id': session_id,
        'reflowed_sessions_count': len(plan_result['sessions']),
        'unscheduled_topics': plan_result['unscheduled_topics']
    }

