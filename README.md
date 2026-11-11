# ClashBoard — Timetable Clash Resolver & Adaptive Study Planner

**ClashBoard** is a desktop application for college students to manage weekly timetables, detect scheduling conflicts automatically, and generate an adaptive study schedule that dynamically reflows when sessions are missed.

Built with **Python 3**, **Tkinter (ttk 'clam' theme)**, and **SQLite3**.

---

## 1. Features

- **Automatic Conflict Detection (`services/clash_detector.py`)**:
  - **Class vs Class**: Detects overlapping timetable slots within the same Day Order.
  - **Class vs Exam**: Detects recurring classes whose Day Order collides with an upcoming exam date.
  - **Exam vs Exam**: Flags critical overlapping exam schedules.
  - Plain-English descriptions and actionable resolution advice.

- **Day Order (DO 1–5) & Calendar Sync (`services/day_order.py`)**:
  - Full Day Order rotational system (Day 1 through Day 5) cycling over academic working days (Mon–Fri).
  - Preserves calendar dates (e.g. `Mon 16 Nov` labeled with `Day 1` badge).
  - Configurable Day Order Anchor / Pivot date in the Weekly Planner.

- **Real Timetable Curriculum**:
  - Populated with authentic college schedule data:
    - **Data Structures (DS)**
    - **Transforms and Techniques (T&T)**
    - **Operating Systems (OS)**
    - **Professional Ethics (PE)**
    - **Universal Human Values II (UHV)**
    - **Computer Organization & Architecture (CO)**
    - **Advanced Programming (AP)**
  - 26 periods mapped across rooms `CLS 403`, `TP 704`, `UB 801`, `UB 714B`, and `ONLINE`.

- **Urgency-Based Greedy Study Scheduler (`services/scheduler.py`)**:
  - Urgency Formula: `(priority * difficulty_level) / max(days_until_exam, 1)`
  - Automatically maps active free time windows (24h minus timetable classes minus 9h sleep & meal buffers).
  - Greedily assigns high-urgency topics to available free slots before exam dates.
  - Flags topics with insufficient free slots before exams.

- **Adaptive Missed-Session Reflow (`reflow_on_missed`)**:
  - Clicking any session in the Weekly Planner to mark it **Missed** immediately re-calculates remaining hours and urgencies, dynamically reflowing all future planned sessions.

- **Left Sidebar Navigation (5 Screens)**:
  1. **Weekly Planner** (Main Screen): Canvas-drawn 7-day grid color-coded by subject, showing background class blocks, exams, and interactive session cards.
  2. **Timetable & Exams**: Add, edit, and delete recurring classes and upcoming exam dates.
  3. **Clash Report**: Conflict severity breakdown with plain-English details and resolution recommendations.
  4. **Subjects & Topics**: Manage subjects (credits, difficulty 1-5) and topics (estimated hours, priority 1-5 adjusted via `ttk.Scale`).
  5. **Progress Dashboard**: Embedded `matplotlib` bar chart (planned vs. completed hours per subject) and stat summary cards.

- **Automatic Demo Seeder (`db/seed.py`)**:
  - Auto-seeds on first run with the authentic 7 college subjects, 26 Day Order timetable slots, upcoming exams, 24 topics, and pre-scheduled study sessions.

---

## 2. Architecture & Design Rules

Strict 3-layer architecture:
```
F:\APP Tkinter\
├── main.py                     # Application entry point
├── clashboard.db               # SQLite database (auto-generated on first run)
├── requirements.txt            # Dependencies
├── README.md                   # Documentation
├── run.bat                     # Windows one-click launcher
├── db/                         # Layer 1: Database (Schema + Queries only)
│   ├── __init__.py
│   ├── connection.py           # SQLite connection with PRAGMA foreign_keys = ON
│   ├── schema.py               # 7 table schemas (with Settings)
│   ├── queries.py              # CRUD queries
│   └── seed.py                 # Authentic college timetable demo data
├── services/                   # Layer 2: Core Logic (Pure functions, zero GUI code)
│   ├── __init__.py
│   ├── day_order.py            # Day Order cycle & calendar date mapping
│   ├── clash_detector.py       # Interval overlap & multi-type clash detection
│   └── scheduler.py            # Urgency calculation, free slots, greedy schedule, reflow
├── gui/                        # Layer 3: Presentation (Tkinter only, ttk 'clam')
│   ├── __init__.py
│   ├── app.py                  # Main window shell & sidebar navigation
│   ├── styles.py               # Clam styling, #2F5233 accent, muted palette, Segoe UI
│   └── screens/
│       ├── __init__.py
│       ├── planner_screen.py   # Canvas 7-day interactive grid with Day Order badges
│       ├── timetable_screen.py # Day Order timetable & exams CRUD
│       ├── clash_screen.py     # Conflict report & guidance
│       ├── subjects_screen.py  # Subjects & topics manager with ttk.Scale
│       └── dashboard_screen.py # Matplotlib bar chart & analytics
└── tests/                      # Automated test suite
    ├── test_db.py
    ├── test_clash_detector.py
    ├── test_gui_smoke.py
    └── test_scheduler.py
```

### Visual Design Rules Enforced
- **Theme**: `ttk.Style().theme_use('clam')`
- **Accent Color**: `#2F5233` (deep forest green)
- **Background**: `#F7F6F2` (warm off-white)
- **Text**: `#1C1C1C`
- **Font**: `Segoe UI` (10pt body, 14pt bold headers)
- **Subject Colors**: Fixed muted palette (Dusty Blue `#5B84B1`, Terracotta `#D46A43`, Sage `#7A9A78`, Mustard `#D9A74A`, Slate `#6B7A82`).

---

## 3. Installation & Setup

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Tkinter (included with standard Python on Windows/macOS)

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 4. Running the Application

Launch ClashBoard with:
```bash
python main.py
```

On first launch, the database (`clashboard.db`) is automatically created and seeded with realistic demo data so the app is instantly interactive.

---

## 5. Running Automated Tests

Run the test suite using `pytest`:
```bash
python -m pytest
```

All unit tests verify:
- Foreign key enforcement and CRUD operations in `db/`
- Interval overlap math, class-class, class-exam, and exam-exam detection in `services/clash_detector.py`
- Urgency formula, free slot derivation, schedule builder, and `reflow_on_missed` in `services/scheduler.py`

