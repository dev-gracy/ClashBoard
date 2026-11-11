"""
Database queries for ClashBoard.
Layer: db/ — zero GUI imports.
All timetable entries now use day_order (1–5) instead of day_of_week.
"""
import datetime


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def get_setting(conn, key, default=None):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM Settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row['value'] if row else default


def set_setting(conn, key, value):
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO Settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SUBJECTS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_subjects(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject_id, name, code, difficulty_level, credits
        FROM Subjects ORDER BY name ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_subject_by_id(conn, subject_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject_id, name, code, difficulty_level, credits
        FROM Subjects WHERE subject_id = ?
    """, (subject_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def insert_subject(conn, name, code, difficulty_level, credits):
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Subjects (name, code, difficulty_level, credits) VALUES (?, ?, ?, ?)",
            (name, code, difficulty_level, credits)
        )
        return cursor.lastrowid


def update_subject(conn, subject_id, name, code, difficulty_level, credits):
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Subjects SET name=?, code=?, difficulty_level=?, credits=?
            WHERE subject_id=?
        """, (name, code, difficulty_level, credits, subject_id))
        return cursor.rowcount > 0


def delete_subject(conn, subject_id):
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Subjects WHERE subject_id=?", (subject_id,))
        return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TIMETABLE  (day_order: 1–5)
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_timetable_slots(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.slot_id, t.subject_id, t.day_order, t.start_time, t.end_time, t.section,
               s.name AS subject_name, s.code AS subject_code, s.difficulty_level
        FROM Timetable t
        JOIN Subjects s ON t.subject_id = s.subject_id
        ORDER BY t.day_order ASC, t.start_time ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_timetable_slots_for_day_order(conn, day_order):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.slot_id, t.subject_id, t.day_order, t.start_time, t.end_time, t.section,
               s.name AS subject_name, s.code AS subject_code, s.difficulty_level
        FROM Timetable t
        JOIN Subjects s ON t.subject_id = s.subject_id
        WHERE t.day_order = ?
        ORDER BY t.start_time ASC
    """, (day_order,))
    return [dict(row) for row in cursor.fetchall()]


def get_timetable_slot_by_id(conn, slot_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.slot_id, t.subject_id, t.day_order, t.start_time, t.end_time, t.section,
               s.name AS subject_name, s.code AS subject_code
        FROM Timetable t
        JOIN Subjects s ON t.subject_id = s.subject_id
        WHERE t.slot_id = ?
    """, (slot_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def insert_timetable_slot(conn, subject_id, day_order, start_time, end_time, section):
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Timetable (subject_id, day_order, start_time, end_time, section) "
            "VALUES (?, ?, ?, ?, ?)",
            (subject_id, day_order, start_time, end_time, section)
        )
        return cursor.lastrowid


def update_timetable_slot(conn, slot_id, subject_id, day_order, start_time, end_time, section):
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Timetable SET subject_id=?, day_order=?, start_time=?, end_time=?, section=?
            WHERE slot_id=?
        """, (subject_id, day_order, start_time, end_time, section, slot_id))
        return cursor.rowcount > 0


def delete_timetable_slot(conn, slot_id):
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Timetable WHERE slot_id=?", (slot_id,))
        return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_exams(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.exam_id, e.subject_id, e.exam_date, e.start_time, e.end_time,
               s.name AS subject_name, s.code AS subject_code, s.difficulty_level
        FROM Exams e
        JOIN Subjects s ON e.subject_id = s.subject_id
        ORDER BY e.exam_date ASC, e.start_time ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_exam_by_id(conn, exam_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.exam_id, e.subject_id, e.exam_date, e.start_time, e.end_time,
               s.name AS subject_name, s.code AS subject_code
        FROM Exams e
        JOIN Subjects s ON e.subject_id = s.subject_id
        WHERE e.exam_id = ?
    """, (exam_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def insert_exam(conn, subject_id, exam_date, start_time, end_time):
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Exams (subject_id, exam_date, start_time, end_time) VALUES (?, ?, ?, ?)",
            (subject_id, exam_date, start_time, end_time)
        )
        return cursor.lastrowid


def update_exam(conn, exam_id, subject_id, exam_date, start_time, end_time):
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Exams SET subject_id=?, exam_date=?, start_time=?, end_time=?
            WHERE exam_id=?
        """, (subject_id, exam_date, start_time, end_time, exam_id))
        return cursor.rowcount > 0


def delete_exam(conn, exam_id):
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Exams WHERE exam_id=?", (exam_id,))
        return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TOPICS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_topics(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.topic_id, t.subject_id, t.topic_name, t.estimated_hours, t.priority,
               s.name AS subject_name, s.code AS subject_code, s.difficulty_level,
               (SELECT MIN(e.exam_date) FROM Exams e WHERE e.subject_id = s.subject_id) AS exam_date
        FROM Topics t
        JOIN Subjects s ON t.subject_id = s.subject_id
        ORDER BY s.name ASC, t.priority DESC, t.topic_name ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_topics_by_subject(conn, subject_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.topic_id, t.subject_id, t.topic_name, t.estimated_hours, t.priority,
               s.name AS subject_name, s.code AS subject_code, s.difficulty_level,
               (SELECT MIN(e.exam_date) FROM Exams e WHERE e.subject_id = s.subject_id) AS exam_date
        FROM Topics t
        JOIN Subjects s ON t.subject_id = s.subject_id
        WHERE t.subject_id = ?
        ORDER BY t.priority DESC, t.topic_name ASC
    """, (subject_id,))
    return [dict(row) for row in cursor.fetchall()]


def get_topic_by_id(conn, topic_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.topic_id, t.subject_id, t.topic_name, t.estimated_hours, t.priority,
               s.name AS subject_name, s.code AS subject_code, s.difficulty_level,
               (SELECT MIN(e.exam_date) FROM Exams e WHERE e.subject_id = s.subject_id) AS exam_date
        FROM Topics t
        JOIN Subjects s ON t.subject_id = s.subject_id
        WHERE t.topic_id = ?
    """, (topic_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def insert_topic(conn, subject_id, topic_name, estimated_hours, priority):
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Topics (subject_id, topic_name, estimated_hours, priority) VALUES (?, ?, ?, ?)",
            (subject_id, topic_name, estimated_hours, priority)
        )
        return cursor.lastrowid


def update_topic(conn, topic_id, subject_id, topic_name, estimated_hours, priority):
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Topics SET subject_id=?, topic_name=?, estimated_hours=?, priority=?
            WHERE topic_id=?
        """, (subject_id, topic_name, estimated_hours, priority, topic_id))
        return cursor.rowcount > 0


def delete_topic(conn, topic_id):
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Topics WHERE topic_id=?", (topic_id,))
        return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
# STUDY SESSIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_study_sessions(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ss.session_id, ss.topic_id, ss.scheduled_date, ss.scheduled_start,
               ss.scheduled_end, ss.status,
               tp.topic_name, tp.estimated_hours, tp.priority,
               sb.subject_id, sb.name AS subject_name, sb.code AS subject_code,
               sb.difficulty_level
        FROM StudySessions ss
        JOIN Topics tp ON ss.topic_id = tp.topic_id
        JOIN Subjects sb ON tp.subject_id = sb.subject_id
        ORDER BY ss.scheduled_date ASC, ss.scheduled_start ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_study_sessions_by_date_range(conn, start_date, end_date):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ss.session_id, ss.topic_id, ss.scheduled_date, ss.scheduled_start,
               ss.scheduled_end, ss.status,
               tp.topic_name, tp.estimated_hours, tp.priority,
               sb.subject_id, sb.name AS subject_name, sb.code AS subject_code,
               sb.difficulty_level
        FROM StudySessions ss
        JOIN Topics tp ON ss.topic_id = tp.topic_id
        JOIN Subjects sb ON tp.subject_id = sb.subject_id
        WHERE ss.scheduled_date BETWEEN ? AND ?
        ORDER BY ss.scheduled_date ASC, ss.scheduled_start ASC
    """, (start_date, end_date))
    return [dict(row) for row in cursor.fetchall()]


def get_study_session_by_id(conn, session_id):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ss.session_id, ss.topic_id, ss.scheduled_date, ss.scheduled_start,
               ss.scheduled_end, ss.status,
               tp.topic_name, tp.estimated_hours, tp.priority,
               sb.subject_id, sb.name AS subject_name, sb.code AS subject_code,
               sb.difficulty_level
        FROM StudySessions ss
        JOIN Topics tp ON ss.topic_id = tp.topic_id
        JOIN Subjects sb ON tp.subject_id = sb.subject_id
        WHERE ss.session_id = ?
    """, (session_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def insert_study_session(conn, topic_id, scheduled_date, scheduled_start, scheduled_end, status='planned'):
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO StudySessions (topic_id, scheduled_date, scheduled_start, scheduled_end, status) "
            "VALUES (?, ?, ?, ?, ?)",
            (topic_id, scheduled_date, scheduled_start, scheduled_end, status)
        )
        return cursor.lastrowid


def update_study_session_status(conn, session_id, status):
    with conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE StudySessions SET status=? WHERE session_id=?", (status, session_id))
        return cursor.rowcount > 0


def delete_study_session(conn, session_id):
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM StudySessions WHERE session_id=?", (session_id,))
        return cursor.rowcount > 0


def clear_planned_study_sessions(conn, from_date=None):
    with conn:
        cursor = conn.cursor()
        if from_date:
            cursor.execute(
                "DELETE FROM StudySessions WHERE status='planned' AND scheduled_date >= ?",
                (from_date,)
            )
        else:
            cursor.execute("DELETE FROM StudySessions WHERE status='planned'")
        return cursor.rowcount


def get_all_sessions_summary_by_subject(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sb.subject_id, sb.name AS subject_name, sb.code AS subject_code,
            COALESCE(SUM(CASE WHEN ss.status='planned' THEN
                (strftime('%s','2000-01-01 '||ss.scheduled_end) -
                 strftime('%s','2000-01-01 '||ss.scheduled_start)) / 3600.0 ELSE 0 END), 0) AS planned_hours,
            COALESCE(SUM(CASE WHEN ss.status='done' THEN
                (strftime('%s','2000-01-01 '||ss.scheduled_end) -
                 strftime('%s','2000-01-01 '||ss.scheduled_start)) / 3600.0 ELSE 0 END), 0) AS done_hours,
            COALESCE(SUM(CASE WHEN ss.status='missed' THEN
                (strftime('%s','2000-01-01 '||ss.scheduled_end) -
                 strftime('%s','2000-01-01 '||ss.scheduled_start)) / 3600.0 ELSE 0 END), 0) AS missed_hours
        FROM Subjects sb
        LEFT JOIN Topics tp ON sb.subject_id = tp.subject_id
        LEFT JOIN StudySessions ss ON tp.topic_id = ss.topic_id
        GROUP BY sb.subject_id ORDER BY sb.name ASC
    """)
    return [dict(row) for row in cursor.fetchall()]


def get_completed_hours_by_subject(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sb.subject_id, sb.name AS subject_name, sb.code AS subject_code,
               SUM((strftime('%s','2000-01-01 '||ss.scheduled_end) -
                    strftime('%s','2000-01-01 '||ss.scheduled_start)) / 3600.0) AS completed_hours
        FROM StudySessions ss
        JOIN Topics tp ON ss.topic_id = tp.topic_id
        JOIN Subjects sb ON tp.subject_id = sb.subject_id
        WHERE ss.status = 'done'
        GROUP BY sb.subject_id
    """)
    return [dict(row) for row in cursor.fetchall()]


# ═══════════════════════════════════════════════════════════════════════════════
# CLASHES
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_clashes(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT clash_id, slot_id_1, slot_id_2, exam_id, clash_type, detected_on, description
        FROM Clashes ORDER BY clash_type ASC, detected_on DESC
    """)
    return [dict(row) for row in cursor.fetchall()]


def save_clashes(conn, clash_list):
    with conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Clashes")
        for c in clash_list:
            cursor.execute("""
                INSERT INTO Clashes (slot_id_1, slot_id_2, exam_id, clash_type, detected_on, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                c.get('slot_id_1'), c.get('slot_id_2'), c.get('exam_id'),
                c.get('clash_type'),
                c.get('detected_on', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                c.get('description', '')
            ))
