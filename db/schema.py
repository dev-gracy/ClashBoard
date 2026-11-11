"""
Database schema definition and initialization for ClashBoard.
Enforces all tables and foreign key relationships.
Handles migration from old day_of_week schema → new day_order schema.
"""


def init_db(conn):
    """
    Initialises the database schema.
    If the old day_of_week column is detected in Timetable, all tables are
    dropped and rebuilt so the new day_order column is used cleanly.
    """
    conn.execute("PRAGMA foreign_keys = ON;")

    # ── Migration guard ──────────────────────────────────────────────────────
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(Timetable)")
    timetable_columns = [row[1] for row in cursor.fetchall()]

    if 'day_of_week' in timetable_columns:
        # Old schema detected → drop everything and let the block below recreate
        with conn:
            conn.executescript("""
                PRAGMA foreign_keys = OFF;
                DROP TABLE IF EXISTS Clashes;
                DROP TABLE IF EXISTS StudySessions;
                DROP TABLE IF EXISTS Topics;
                DROP TABLE IF EXISTS Exams;
                DROP TABLE IF EXISTS Timetable;
                DROP TABLE IF EXISTS Subjects;
                DROP TABLE IF EXISTS Settings;
                PRAGMA foreign_keys = ON;
            """)

    # ── Create all tables ────────────────────────────────────────────────────
    with conn:
        conn.executescript("""
        -- Key-value store for app-wide configuration
        CREATE TABLE IF NOT EXISTS Settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS Subjects (
            subject_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT NOT NULL,
            code             TEXT,
            difficulty_level INTEGER,   -- 1 (easy) to 5 (hard)
            credits          INTEGER
        );

        -- day_order: 1=DO1, 2=DO2, 3=DO3, 4=DO4, 5=DO5
        CREATE TABLE IF NOT EXISTS Timetable (
            slot_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id) ON DELETE CASCADE,
            day_order  INTEGER NOT NULL,
            start_time TEXT NOT NULL,   -- 'HH:MM' 24-hr
            end_time   TEXT NOT NULL,   -- 'HH:MM' 24-hr
            section    TEXT             -- room / section / mode
        );

        CREATE TABLE IF NOT EXISTS Exams (
            exam_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id) ON DELETE CASCADE,
            exam_date  TEXT NOT NULL,   -- 'YYYY-MM-DD'
            start_time TEXT NOT NULL,
            end_time   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Topics (
            topic_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id     INTEGER NOT NULL REFERENCES Subjects(subject_id) ON DELETE CASCADE,
            topic_name     TEXT NOT NULL,
            estimated_hours REAL,
            priority        INTEGER     -- 1 (low) to 5 (high)
        );

        CREATE TABLE IF NOT EXISTS StudySessions (
            session_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id        INTEGER NOT NULL REFERENCES Topics(topic_id) ON DELETE CASCADE,
            scheduled_date  TEXT,       -- 'YYYY-MM-DD'
            scheduled_start TEXT,
            scheduled_end   TEXT,
            status          TEXT DEFAULT 'planned'  -- 'planned' | 'done' | 'missed'
        );

        CREATE TABLE IF NOT EXISTS Clashes (
            clash_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_id_1   INTEGER REFERENCES Timetable(slot_id) ON DELETE CASCADE,
            slot_id_2   INTEGER REFERENCES Timetable(slot_id) ON DELETE CASCADE,
            exam_id     INTEGER REFERENCES Exams(exam_id) ON DELETE CASCADE,
            clash_type  TEXT,           -- 'class-class' | 'class-exam' | 'exam-exam'
            detected_on TEXT,
            description TEXT
        );
        """)
