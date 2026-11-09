"""
Database Seeder for ClashBoard.
Populates realistic demo data on first run:
- 6 subjects with varied difficulty and credits
- ~15 weekly timetable slots with an intentional class-class clash
- 4 upcoming exams with intentional exam-exam and class-exam clashes
- 3-4 topics per subject with varied priorities
- Pre-scanned clash records
- Pre-scheduled study sessions with planned and done statuses
"""
import datetime
from db import queries
from services.clash_detector import detect_clashes
from services.scheduler import get_free_slots, build_schedule


def seed_database(conn, force=False):
    """
    Seeds the database if Subjects table is empty (or if force=True).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Subjects")
    count = cursor.fetchone()[0]
    if count > 0 and not force:
        return False  # Already seeded

    # Clear existing data if forced
    if force:
        with conn:
            conn.execute("DELETE FROM Clashes")
            conn.execute("DELETE FROM StudySessions")
            conn.execute("DELETE FROM Topics")
            conn.execute("DELETE FROM Exams")
            conn.execute("DELETE FROM Timetable")
            conn.execute("DELETE FROM Subjects")

    today = datetime.date.today()

    # 1. SUBJECTS
    subjects_data = [
        {"name": "Data Structures & Algorithms", "code": "CS301", "difficulty_level": 4, "credits": 4},
        {"name": "Operating Systems", "code": "CS302", "difficulty_level": 4, "credits": 4},
        {"name": "Linear Algebra & Optimization", "code": "MA201", "difficulty_level": 5, "credits": 4},
        {"name": "Computer Networks", "code": "CS303", "difficulty_level": 3, "credits": 3},
        {"name": "Digital Logic & Architecture", "code": "EC201", "difficulty_level": 3, "credits": 3},
        {"name": "Professional Ethics & Comm", "code": "HS101", "difficulty_level": 1, "credits": 2},
    ]

    subject_ids = {}
    for s in subjects_data:
        sid = queries.insert_subject(conn, s["name"], s["code"], s["difficulty_level"], s["credits"])
        subject_ids[s["code"]] = sid

    # 2. TIMETABLE SLOTS (~15 slots)
    # Includes an intentional clash on Monday (11:00 - 11:30 overlap)
    timetable_data = [
        # Monday
        {"code": "CS301", "day": "Mon", "start": "10:00", "end": "11:30", "sec": "Lecture L1"},
        {"code": "EC201", "day": "Mon", "start": "11:00", "end": "12:30", "sec": "Lab B2"},  # Clashes with CS301 (11:00-11:30)
        {"code": "MA201", "day": "Mon", "start": "14:00", "end": "15:30", "sec": "Lecture"},
        # Tuesday
        {"code": "CS302", "day": "Tue", "start": "09:00", "end": "10:30", "sec": "Lecture"},
        {"code": "CS303", "day": "Tue", "start": "11:00", "end": "12:30", "sec": "Lecture"},
        {"code": "HS101", "day": "Tue", "start": "14:00", "end": "15:30", "sec": "Seminar"},
        # Wednesday
        {"code": "CS301", "day": "Wed", "start": "10:00", "end": "11:30", "sec": "Tutorial"},
        {"code": "MA201", "day": "Wed", "start": "12:00", "end": "13:30", "sec": "Problem Set"},
        {"code": "EC201", "day": "Wed", "start": "15:00", "end": "16:30", "sec": "Lecture"},
        # Thursday
        {"code": "CS302", "day": "Thu", "start": "09:00", "end": "11:00", "sec": "Lab OS"},
        {"code": "CS303", "day": "Thu", "start": "11:30", "end": "13:00", "sec": "Lecture"},
        {"code": "MA201", "day": "Thu", "start": "14:00", "end": "15:30", "sec": "Tutorial"},
        # Friday
        {"code": "CS301", "day": "Fri", "start": "10:00", "end": "11:30", "sec": "Lecture L2"},
        {"code": "CS303", "day": "Fri", "start": "12:00", "end": "13:30", "sec": "Network Lab"},
        {"code": "HS101", "day": "Fri", "start": "14:30", "end": "16:00", "sec": "Discussion"},
    ]

    for t in timetable_data:
        queries.insert_timetable_slot(
            conn,
            subject_id=subject_ids[t["code"]],
            day_of_week=t["day"],
            start_time=t["start"],
            end_time=t["end"],
            section=t["sec"]
        )

    # 3. UPCOMING EXAMS
    # Place exams on specific dates relative to today
    # Find next Monday for a class-exam clash
    days_to_next_mon = (0 - today.weekday() + 7) % 7
    if days_to_next_mon == 0:
        days_to_next_mon = 7
    next_mon = today + datetime.timedelta(days=days_to_next_mon)
    
    exam_date_1 = (today + datetime.timedelta(days=8)).strftime("%Y-%m-%d")
    exam_date_2 = (today + datetime.timedelta(days=12)).strftime("%Y-%m-%d")
    exam_date_mon = next_mon.strftime("%Y-%m-%d")

    exams_data = [
        # Clashes with Monday 10:00-11:30 class
        {"code": "CS301", "date": exam_date_mon, "start": "10:30", "end": "12:30"},
        # Same date exams (exam_date_2) -> Exam-Exam clash (14:30 - 16:00 overlap)
        {"code": "MA201", "date": exam_date_2, "start": "14:00", "end": "16:00"},
        {"code": "CS302", "date": exam_date_2, "start": "14:30", "end": "16:30"},
        # Non-clashing exam
        {"code": "CS303", "date": exam_date_1, "start": "09:00", "end": "11:00"},
    ]

    for e in exams_data:
        queries.insert_exam(
            conn,
            subject_id=subject_ids[e["code"]],
            exam_date=e["date"],
            start_time=e["start"],
            end_time=e["end"]
        )

    # 4. TOPICS (3-4 topics per subject)
    topics_data = [
        # CS301 (Difficulty 4)
        {"code": "CS301", "name": "Binary Search Trees & AVL", "hours": 3.0, "priority": 5},
        {"code": "CS301", "name": "Graph Algorithms (Dijkstra)", "hours": 3.5, "priority": 5},
        {"code": "CS301", "name": "Dynamic Programming Patterns", "hours": 4.0, "priority": 5},
        {"code": "CS301", "name": "Hash Tables & Collisions", "hours": 2.0, "priority": 3},
        # CS302 (Difficulty 4)
        {"code": "CS302", "name": "Process Sync & Semaphores", "hours": 3.0, "priority": 4},
        {"code": "CS302", "name": "Virtual Memory & Paging", "hours": 2.5, "priority": 4},
        {"code": "CS302", "name": "Banker's Algorithm & Deadlocks", "hours": 2.0, "priority": 4},
        {"code": "CS302", "name": "File System Architecture", "hours": 1.5, "priority": 2},
        # MA201 (Difficulty 5)
        {"code": "MA201", "name": "Eigenvalues & Diagonalization", "hours": 3.5, "priority": 5},
        {"code": "MA201", "name": "Singular Value Decomposition (SVD)", "hours": 4.0, "priority": 5},
        {"code": "MA201", "name": "Vector Spaces & Orthogonality", "hours": 3.0, "priority": 4},
        {"code": "MA201", "name": "Convex Optimization", "hours": 2.0, "priority": 3},
        # CS303 (Difficulty 3)
        {"code": "CS303", "name": "TCP Congestion & Flow Control", "hours": 2.5, "priority": 3},
        {"code": "CS303", "name": "IP Subnetting & CIDR", "hours": 2.0, "priority": 4},
        {"code": "CS303", "name": "Routing Protocols (OSPF/BGP)", "hours": 2.0, "priority": 3},
        # EC201 (Difficulty 3)
        {"code": "EC201", "name": "Karnaugh Maps & Combinational Logic", "hours": 2.0, "priority": 3},
        {"code": "EC201", "name": "Sequential Circuits & Flip-Flops", "hours": 2.5, "priority": 3},
        {"code": "EC201", "name": "ALU & Pipelined Datapath", "hours": 2.5, "priority": 3},
        # HS101 (Difficulty 1)
        {"code": "HS101", "name": "Technical Paper Style & Citations", "hours": 1.5, "priority": 1},
        {"code": "HS101", "name": "Engineering Ethics Case Studies", "hours": 1.5, "priority": 2},
    ]

    for tp in topics_data:
        queries.insert_topic(
            conn,
            subject_id=subject_ids[tp["code"]],
            topic_name=tp["name"],
            estimated_hours=tp["hours"],
            priority=tp["priority"]
        )

    # 5. DETECT INITIAL CLASHES & SAVE
    slots = queries.get_all_timetable_slots(conn)
    all_exams = queries.get_all_exams(conn)
    detected = detect_clashes(slots, all_exams)
    queries.save_clashes(conn, detected)

    # 6. BUILD INITIAL STUDY SCHEDULE
    all_topics = queries.get_all_topics(conn)
    planning_days = [today + datetime.timedelta(days=i) for i in range(14)]
    free_slots = get_free_slots(slots, planning_days, exams=all_exams)
    schedule_result = build_schedule(all_topics, free_slots, reference_date=today)

    # Insert planned sessions
    # Mark the first session as 'done' to demonstrate progress in dashboard and planner
    for idx, s in enumerate(schedule_result['sessions']):
        status = 'done' if idx == 0 else 'planned'
        queries.insert_study_session(
            conn,
            topic_id=s['topic_id'],
            scheduled_date=s['scheduled_date'],
            scheduled_start=s['scheduled_start'],
            scheduled_end=s['scheduled_end'],
            status=status
        )

    return True

