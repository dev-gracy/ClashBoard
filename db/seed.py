"""
Database Seeder for ClashBoard.
Populated from the actual timetable image (Day Order 1–5 system).

Subjects (from timetable):
  DS  — Data Structures              (Dr. Ramachandran)
  T&T — Transforms and Techniques    (Dr. V. Raja, 103175)
  OS  — Operating Systems            (Dr. S. Priyadharshini)
  PE  — Professional Ethics          (Dr. J. Michael Raj)
  UHV — Universal Human Values II    (Dr. Poongothai E)
  CO  — Computer Organization & Arch (Dr. M. Maheswari)
  AP  — Advanced Programming         (Dr. Suresh Anand M.)

Time slots (24-hr):
  P1  08:00–08:50   P2  08:50–09:40
  P3  09:45–10:35   P4  10:40–11:30
  P5  11:35–12:25   P6  12:30–13:20
  P7  13:25–14:15   P8  14:20–15:10
  P9  15:10–16:00   P10 16:00–16:50
"""
import datetime
from db import queries
from services.clash_detector import detect_clashes
from services.scheduler import get_free_slots, build_schedule


def seed_database(conn, force=False):
    """Seeds the database if empty (or if force=True)."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Subjects")
    if cursor.fetchone()[0] > 0 and not force:
        return False

    # ── Clear existing data ──────────────────────────────────────────────────
    with conn:
        conn.executescript("""
            PRAGMA foreign_keys = OFF;
            DELETE FROM Clashes;
            DELETE FROM StudySessions;
            DELETE FROM Topics;
            DELETE FROM Exams;
            DELETE FROM Timetable;
            DELETE FROM Subjects;
            DELETE FROM Settings;
            DELETE FROM sqlite_sequence WHERE name IN
                ('Clashes','StudySessions','Topics','Exams','Timetable','Subjects');
            PRAGMA foreign_keys = ON;
        """)

    today = datetime.date.today()

    # ── Pivot: This week's Monday = Day Order 1 ──────────────────────────────
    monday = today - datetime.timedelta(days=today.weekday())
    queries.set_setting(conn, 'pivot_date', monday.strftime('%Y-%m-%d'))
    queries.set_setting(conn, 'pivot_day_order', '1')

    # ════════════════════════════════════════════════════════════════════════
    # 1. SUBJECTS
    # ════════════════════════════════════════════════════════════════════════
    subjects_data = [
        # (name, code, difficulty 1–5, credits)
        ("Data Structures",                 "DS",  4, 4),
        ("Transforms and Techniques",       "T&T", 5, 4),
        ("Operating Systems",               "OS",  4, 4),
        ("Professional Ethics",             "PE",  1, 2),
        ("Universal Human Values II",       "UHV", 1, 2),
        ("Computer Organization & Arch",    "CO",  3, 4),
        ("Advanced Programming",            "AP",  3, 4),
    ]
    sid = {}   # code → subject_id
    for name, code, diff, cred in subjects_data:
        sid[code] = queries.insert_subject(conn, name, code, diff, cred)

    # ════════════════════════════════════════════════════════════════════════
    # 2. TIMETABLE  (read directly from the uploaded image, Day Order 1–5)
    # ════════════════════════════════════════════════════════════════════════
    # Format: (subject_code, day_order, start_time, end_time, room/section)
    timetable_data = [
        # ── Day Order 1 ────────────────────────────────────────────────────
        ("DS",  1, "09:45", "10:35", "CLS 403"),   # P3
        ("DS",  1, "10:40", "11:30", "CLS 403"),   # P4
        ("T&T", 1, "12:30", "13:20", "TP 704"),    # P6
        ("T&T", 1, "13:25", "14:15", "TP 704"),    # P7
        ("OS",  1, "14:20", "15:10", "TP 704"),    # P8
        ("OS",  1, "15:10", "16:00", "TP 704"),    # P9

        # ── Day Order 2 ────────────────────────────────────────────────────
        ("DS",  2, "08:00", "08:50", "TP 704"),    # P1
        ("DS",  2, "08:50", "09:40", "TP 704"),    # P2
        ("T&T", 2, "11:35", "12:25", "TP 704"),    # P5
        ("PE",  2, "12:30", "13:20", "ONLINE"),    # P6
        ("UHV", 2, "13:25", "14:15", "UB 801"),   # P7
        ("UHV", 2, "14:20", "15:10", "UB 801"),   # P8

        # ── Day Order 3 ────────────────────────────────────────────────────
        ("CO",  3, "12:30", "13:20", "TP 704"),    # P6
        ("CO",  3, "13:25", "14:15", "TP 704"),    # P7
        ("T&T", 3, "14:20", "15:10", "TP 704"),    # P8
        ("AP",  3, "15:10", "16:00", "TP 704"),    # P9
        ("DS",  3, "16:00", "16:50", "TP 704"),    # P10

        # ── Day Order 4 ────────────────────────────────────────────────────
        ("AP",  4, "08:00", "08:50", "TP 704"),    # P1
        ("AP",  4, "08:50", "09:40", "TP 704"),    # P2
        ("DS",  4, "09:45", "10:35", "TP 704"),    # P3
        ("CO",  4, "11:35", "12:25", "TP 704"),    # P5
        ("OS",  4, "15:10", "16:00", "UB 714B"),   # P9
        ("OS",  4, "16:00", "16:50", "UB 714B"),   # P10

        # ── Day Order 5 ────────────────────────────────────────────────────
        ("CO",  5, "14:20", "15:10", "TP 704"),    # P8
        ("OS",  5, "15:10", "16:00", "TP 704"),    # P9
        ("AP",  5, "16:00", "16:50", "TP 704"),    # P10
    ]

    for code, do, st, et, room in timetable_data:
        queries.insert_timetable_slot(conn, sid[code], do, st, et, room)

    # ════════════════════════════════════════════════════════════════════════
    # 3. UPCOMING EXAMS
    # Seed exams a few weeks out for the main technical subjects.
    # Also plant a deliberate exam-exam clash on the same date for DS and T&T.
    # ════════════════════════════════════════════════════════════════════════
    exam_date_1 = (today + datetime.timedelta(days=10)).strftime("%Y-%m-%d")  # DS
    exam_date_2 = (today + datetime.timedelta(days=14)).strftime("%Y-%m-%d")  # T&T + OS clash
    exam_date_3 = (today + datetime.timedelta(days=21)).strftime("%Y-%m-%d")  # CO + AP

    exams_data = [
        # (subject_code, exam_date, start, end)
        ("DS",  exam_date_1, "09:00", "12:00"),
        ("T&T", exam_date_2, "09:00", "12:00"),
        ("OS",  exam_date_2, "10:00", "13:00"),   # Clashes with T&T (10:00–12:00 overlap)
        ("CO",  exam_date_3, "09:00", "12:00"),
        ("AP",  exam_date_3, "14:00", "17:00"),
    ]
    for code, edate, st, et in exams_data:
        queries.insert_exam(conn, sid[code], edate, st, et)

    # ════════════════════════════════════════════════════════════════════════
    # 4. TOPICS  (3–4 per subject, based on actual syllabus)
    # ════════════════════════════════════════════════════════════════════════
    topics_data = [
        # (subject_code, topic_name, estimated_hours, priority)

        # Data Structures
        ("DS",  "Arrays, Stacks, and Queues",         2.0, 3),
        ("DS",  "Linked Lists and Variants",           2.0, 3),
        ("DS",  "Binary Search Trees and AVL Trees",   3.0, 5),
        ("DS",  "Graph Algorithms (BFS/DFS/Dijkstra)", 3.5, 5),
        ("DS",  "Hashing and Collision Resolution",    2.0, 4),

        # Transforms and Techniques
        ("T&T", "Fourier Series and Transforms",       3.5, 5),
        ("T&T", "Laplace Transforms",                  3.0, 5),
        ("T&T", "Z-Transforms and Discrete Systems",   3.0, 4),
        ("T&T", "Numerical Methods: Interpolation",    2.5, 4),

        # Operating Systems
        ("OS",  "Process Scheduling Algorithms",       2.5, 4),
        ("OS",  "Deadlocks and Banker's Algorithm",    2.5, 5),
        ("OS",  "Virtual Memory and Page Replacement", 3.0, 5),
        ("OS",  "File System Implementation",          2.0, 3),

        # Professional Ethics
        ("PE",  "Engineering Ethics Frameworks",       1.5, 2),
        ("PE",  "Intellectual Property and Plagiarism",1.0, 1),

        # Universal Human Values II
        ("UHV", "Self-Exploration and Human Goal",     1.5, 2),
        ("UHV", "Harmony in Society and Nature",       1.5, 1),

        # Computer Organization & Architecture
        ("CO",  "ALU Design and Datapath",             2.5, 4),
        ("CO",  "Pipelined Processor Architecture",    3.0, 5),
        ("CO",  "Memory Hierarchy and Cache Design",   2.5, 4),
        ("CO",  "I/O Systems and Interrupts",          2.0, 3),

        # Advanced Programming
        ("AP",  "OOP: Inheritance and Polymorphism",   2.0, 3),
        ("AP",  "Exception Handling and File I/O",     2.0, 3),
        ("AP",  "Multi-threading and Concurrency",     2.5, 4),
        ("AP",  "Data Structures in Python/Java",      2.0, 4),
    ]

    for code, tname, hrs, prio in topics_data:
        queries.insert_topic(conn, sid[code], tname, hrs, prio)

    # ════════════════════════════════════════════════════════════════════════
    # 5. DETECT INITIAL CLASHES
    # ════════════════════════════════════════════════════════════════════════
    slots = queries.get_all_timetable_slots(conn)
    all_exams = queries.get_all_exams(conn)
    pivot_date = queries.get_setting(conn, 'pivot_date')
    pivot_do   = int(queries.get_setting(conn, 'pivot_day_order', '1'))
    detected   = detect_clashes(slots, all_exams, pivot_date, pivot_do)
    queries.save_clashes(conn, detected)

    # ════════════════════════════════════════════════════════════════════════
    # 6. BUILD INITIAL STUDY SCHEDULE (next 21 working days)
    # ════════════════════════════════════════════════════════════════════════
    all_topics    = queries.get_all_topics(conn)
    planning_days = [today + datetime.timedelta(days=i) for i in range(21)]
    free_slots    = get_free_slots(slots, planning_days, all_exams, pivot_date, pivot_do)
    plan          = build_schedule(all_topics, free_slots, reference_date=today)

    # Insert all planned sessions; mark first one 'done' as a demo
    for idx, s in enumerate(plan['sessions']):
        queries.insert_study_session(
            conn,
            topic_id        = s['topic_id'],
            scheduled_date  = s['scheduled_date'],
            scheduled_start = s['scheduled_start'],
            scheduled_end   = s['scheduled_end'],
            status          = 'done' if idx == 0 else 'planned',
        )

    return True
