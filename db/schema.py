"""
Database schema definition and initialization for ClashBoard.
Enforces all 6 tables and foreign key relationships.
"""

def init_db(conn):
    """
    Initializes the database schema if tables do not exist.
    """
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS Subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            difficulty_level INTEGER,   -- 1 (easy) to 5 (hard)
            credits INTEGER
        );

        CREATE TABLE IF NOT EXISTS Timetable (
            slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id) ON DELETE CASCADE,
            day_of_week TEXT NOT NULL,   -- 'Mon'..'Sun'
            start_time TEXT NOT NULL,    -- 'HH:MM', 24-hr
            end_time TEXT NOT NULL,      -- 'HH:MM', 24-hr
            section TEXT
        );

        CREATE TABLE IF NOT EXISTS Exams (
            exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id) ON DELETE CASCADE,
            exam_date TEXT NOT NULL,     -- 'YYYY-MM-DD'
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Topics (
            topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id) ON DELETE CASCADE,
            topic_name TEXT NOT NULL,
            estimated_hours REAL,
            priority INTEGER            -- 1 (low) to 5 (high), student-set
        );

        CREATE TABLE IF NOT EXISTS StudySessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL REFERENCES Topics(topic_id) ON DELETE CASCADE,
            scheduled_date TEXT,        -- 'YYYY-MM-DD'
            scheduled_start TEXT,
            scheduled_end TEXT,
            status TEXT DEFAULT 'planned'   -- 'planned' | 'done' | 'missed'
        );

        CREATE TABLE IF NOT EXISTS Clashes (
            clash_id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_id_1 INTEGER REFERENCES Timetable(slot_id) ON DELETE CASCADE,
            slot_id_2 INTEGER REFERENCES Timetable(slot_id) ON DELETE CASCADE,
            exam_id INTEGER REFERENCES Exams(exam_id) ON DELETE CASCADE,
            clash_type TEXT,            -- 'class-class' | 'class-exam' | 'exam-exam'
            detected_on TEXT,           -- timestamp of detection
            description TEXT
        );
        """)

