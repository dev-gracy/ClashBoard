# ClashBoard — Complete Project Specification

Build a complete, runnable desktop application called **ClashBoard**: a personal timetable clash resolver and adaptive study planner for students.

---

## 1. Product Overview

**Problem:** Students' timetables (lectures, labs, electives) and exam schedules often overlap without anyone noticing until it's too late. Separately, once exams are announced, revision time gets allocated randomly instead of by what's actually urgent, and a single missed study session derails the rest of the week with no automatic recovery.

**Solution:** ClashBoard takes a student's real weekly timetable and upcoming exams, automatically detects every scheduling conflict, and converts free time into a prioritized study plan. If a planned study session is missed, the app recalculates urgency and reflows the remaining schedule automatically.

**Users:** College students managing their own timetable and exam prep.

**Core value:** Automatic conflict detection + a study plan that adapts when things go wrong, instead of a static plan that falls apart after the first missed session.

---

## 2. Technical Requirements (hard constraints — do not deviate)

| Layer | Choice |
|---|---|
| GUI | **Tkinter only**, using `ttk` themed widgets, theme `'clam'` |
| Database | **SQLite**, via Python's built-in `sqlite3` module |
| Language | Python 3 |
| Architecture | Three separate layers in three folders: `db/` (schema + queries only), `services/` (clash detection + scheduler — pure functions, zero Tkinter imports, unit-testable on their own), `gui/` (all Tkinter screens, calling into `services/` and `db/`) |
| Charting (optional) | `matplotlib` embedded via `FigureCanvasTkAgg`, only for the optional dashboard screen |

No web framework, no external GUI toolkit, no cloud database. This is a local desktop app.

---

## 3. Database Schema (SQLite)

Create all six tables with foreign keys enforced.

```sql
CREATE TABLE Subjects (
    subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT,
    difficulty_level INTEGER,   -- 1 (easy) to 5 (hard)
    credits INTEGER
);

CREATE TABLE Timetable (
    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id),
    day_of_week TEXT NOT NULL,   -- 'Mon'..'Sun'
    start_time TEXT NOT NULL,    -- 'HH:MM', 24-hr
    end_time TEXT NOT NULL,      -- 'HH:MM', 24-hr
    section TEXT
);

CREATE TABLE Exams (
    exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id),
    exam_date TEXT NOT NULL,     -- 'YYYY-MM-DD'
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);

CREATE TABLE Topics (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL REFERENCES Subjects(subject_id),
    topic_name TEXT NOT NULL,
    estimated_hours REAL,
    priority INTEGER            -- 1 (low) to 5 (high), student-set
);

CREATE TABLE StudySessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES Topics(topic_id),
    scheduled_date TEXT,        -- 'YYYY-MM-DD'
    scheduled_start TEXT,
    scheduled_end TEXT,
    status TEXT DEFAULT 'planned'   -- 'planned' | 'done' | 'missed'
);

CREATE TABLE Clashes (
    clash_id INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_id_1 INTEGER REFERENCES Timetable(slot_id),
    slot_id_2 INTEGER REFERENCES Timetable(slot_id),
    exam_id INTEGER REFERENCES Exams(exam_id),
    clash_type TEXT,            -- 'class-class' | 'class-exam' | 'exam-exam'
    detected_on TEXT            -- timestamp of detection
);
```

---

## 4. Core Logic (in `services/`, pure functions, no GUI code)

### 4.1 Clash Detection — interval overlap

```python
def ranges_overlap(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a

def detect_clashes(timetable_entries, exams):
    """
    Compare every same-day pair of timetable entries -> clash_type 'class-class'.
    Compare every timetable entry against exams on the same date -> 'class-exam'.
    Compare every pair of exams on the same date -> 'exam-exam'.
    Group entries by day/date first, then check ranges_overlap() pairwise within each group.
    Return a list of dicts ready to insert into the Clashes table,
    each with a plain-English description, e.g.
    "DAA lecture overlaps Physics lab, Tue 10:00-11:00".
    """
```

### 4.2 Study Scheduler — urgency-based greedy allocation

```python
def compute_urgency(priority, difficulty_level, days_until_exam):
    return (priority * difficulty_level) / max(days_until_exam, 1)

def get_free_slots(timetable_entries, date_range):
    """
    For each day in date_range: 24 hours minus that day's Timetable entries
    minus a fixed sleep/meals buffer (hardcode ~9 hours total).
    Return a list of free time windows per day.
    """

def build_schedule(topics, free_slots):
    """
    Sort topics by compute_urgency() descending.
    Walk free_slots in date order; for each topic, allocate its
    estimated_hours, splitting across multiple slots/days if one
    slot isn't enough, until every topic is scheduled or slots run out.
    Return a list of StudySessions rows with status='planned'.
    If a topic cannot be fully scheduled before its exam date, flag it
    clearly in the UI rather than silently dropping hours.
    """

def reflow_on_missed(session_id):
    """
    Mark the given session's status as 'missed'.
    Recompute urgency for its topic (same formula — days_until_exam
    has now shrunk, so urgency rises).
    Re-run build_schedule() over only the remaining free slots from
    today onward, and update StudySessions accordingly.
    This must visibly change the planner view when called.
    """
```

---

## 5. Screens (Tkinter — sidebar navigation on the left, NOT a top tab bar)

1. **Timetable** — add/edit/delete entries via a form; weekly grid view (`ttk.Treeview` or Canvas-drawn table)
2. **Clash Report** — list of detected conflicts in plain English, grouped by type
3. **Subjects & Topics** — subject list, expandable to topics, priority set via `ttk.Scale`
4. **Weekly Planner** (main screen) — Canvas-drawn 7-day grid, sessions color-coded by subject, click a session to mark Done/Missed (Missed triggers `reflow_on_missed` and the grid must visibly update)
5. **Dashboard** (optional, build only if time permits) — matplotlib bar chart: planned vs. completed hours per subject

---

## 6. Visual Design — must NOT look like default Tkinter

| Element | Spec |
|---|---|
| Theme | `ttk.Style().theme_use('clam')` |
| Accent color | `#2F5233` (deep forest green) — the only accent color used anywhere |
| Background | `#F7F6F2` (warm off-white), never default grey |
| Text | `#1C1C1C`, never pure black |
| Subject colors | Fixed muted palette, reused consistently: dusty blue, terracotta, sage, mustard, slate |
| Font | `('Segoe UI', 10)` body, `('Segoe UI', 14, 'bold')` headers |
| Buttons | Flat relief, accent-colored for primary actions, 8-12px padding — never Tkinter's default raised grey button |
| Grouping | `ttk.LabelFrame` for sections, generous whitespace, no widgets butted together with no padding |

Starter style block to use as the base:

```python
style = ttk.Style()
style.theme_use('clam')
style.configure('TFrame', background='#F7F6F2')
style.configure('TLabel', background='#F7F6F2', foreground='#1C1C1C', font=('Segoe UI', 10))
style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'), foreground='#2F5233')
style.configure('Accent.TButton', background='#2F5233', foreground='white',
                font=('Segoe UI', 10, 'bold'), relief='flat', padding=8)
style.map('Accent.TButton', background=[('active', '#3E6B45')])
```

---

## 7. Seed Data

On first run, auto-seed the database with a realistic example: 5-6 subjects, ~15 weekly timetable slots spread Mon-Fri, 2-3 upcoming exams, 3-4 topics per subject with varied priority/difficulty — so the app is demoable immediately with no manual data entry.

---

## 8. Build Order

1. Database schema + seed data
2. Clash detection logic (`services/`) — testable standalone
3. Scheduler logic (`services/`) — testable standalone
4. GUI shell: sidebar nav, Timetable screen, Clash Report screen
5. Weekly Planner screen + Done/Missed interaction wired to `reflow_on_missed`
6. Subjects & Topics screen
7. Styling pass (apply section 6 fully)
8. Optional dashboard screen
9. Edge-case handling: midnight-crossing times, zero free slots before an exam, duplicate entries

---

## 9. Deliverable

A complete, runnable Python project:
- `main.py` — entry point
- `db/` — schema creation + query functions
- `services/` — clash detection + scheduler (pure functions)
- `gui/` — all Tkinter screens
- `requirements.txt` (include `matplotlib` only if the dashboard is built)
- `README.md` with setup and run instructions

Build everything end to end now — schema, logic, all screens, styling, and seed data — as a single working application.
