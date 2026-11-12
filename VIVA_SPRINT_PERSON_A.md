# ClashBoard — Architecture & Integration Viva Sprint (Person A)

> **Role:** System Architect & Integration Lead (Person A)  
> **Topic:** 3-Tier Layered Architecture, Screen Orchestration, Inter-Layer Data Flow, Decoupling & Lifecycle

---

## 1. 45-Second Opening Speech in Viva

When the examiner asks: *"Person A, tell us about the architecture and design of this application"*:

> *"Good morning/afternoon, professors. I am Person A, responsible for the **System Architecture, Component Integration, and Application Lifecycle** of ClashBoard.
>
> Many student desktop applications suffer from tight coupling, where Tkinter event handlers directly execute raw SQL queries. This leads to brittle code that crashes easily and cannot be unit-tested.
>
> For ClashBoard, I implemented a strict **3-Tier Layered Architecture**:
> 1. **Presentation Layer (`gui/`)**: Built entirely with Tkinter and themed ttk widgets (`clam` theme). It handles only rendering, layout, and user events.
> 2. **Business Logic Layer (`services/`)**: Contains pure mathematical functions for Day Order rotation, interval overlap checking, and greedy scheduling. It has **zero Tkinter imports**, making it completely decoupled and testable via PyTest.
> 3. **Persistence Layer (`db/`)**: An isolated SQLite layer with a connection factory enforcing foreign key cascading (`PRAGMA foreign_keys = ON;`) and parameterized queries.
>
> Let me show you the entry point, the screen orchestrator, and how data flows across these three layers in our code."*

---

## 2. "Where is the Code for This?" — Code Map & File Locations

When the examiner asks: *"Show me the code for your architecture"*, open these exact files in VS Code / your editor:

### 2.1 The Application Entry Point & Boot Sequence
* **File:** `main.py`
* **What to show & say:**
  > *"Here in `main.py`, you can see the startup sequence of our application:*
  > 1. *It calls `get_connection()` from `db/connection.py` to establish the SQLite database connection.*
  > 2. *It calls `init_db(conn)` from `db/schema.py` to ensure all 7 tables exist.*
  > 3. *It calls `seed_database(conn)` from `db/seed.py` so the app is immediately populated with our college timetable.*
  > 4. *It instantiates `ClashBoardApp(conn)` and starts the Tkinter event loop `app.mainloop()`.*
  > 5. *In the `finally` block, it guarantees the database connection is cleanly closed upon application exit."*

---

### 2.2 The Navigation Shell & Screen Orchestrator
* **File:** `gui/app.py`
* **Key Class:** `class ClashBoardApp(tk.Tk)`
* **Code to point at:**
  - **Lines 44–68 (`_build_layout` and `_build_sidebar`):** Master window split into a fixed left sidebar (`width=240`, `Sidebar.TFrame`) and a dynamic content container on the right.
  - **Lines 141–178 (`_init_screens`):**
    ```python
    self.screens['planner'] = PlannerScreen(self.content_container, self.conn, ...)
    self.screens['timetable'] = TimetableScreen(self.content_container, self.conn, ...)
    self.screens['clashes'] = ClashScreen(self.content_container, self.conn, ...)
    self.screens['subjects'] = SubjectsScreen(self.content_container, self.conn, ...)
    self.screens['dashboard'] = DashboardScreen(self.content_container, self.conn)
    ```
    > *"All 5 screens are instantiated once and stored inside a dictionary container `self.screens`."*
  - **Lines 180–200 (`show_screen(screen_key)`):**
    > *"This is our screen-switching design pattern. We do not destroy windows or create popups for main screens. When a user clicks a sidebar button, we call `pack_forget()` on the current screen and `pack(fill='both', expand=True)` on the target screen, followed by `target_screen.refresh()` to fetch the latest state from SQLite."*

---

### 2.3 The Centralized Styling Subsystem
* **File:** `gui/styles.py`
* **Key Function:** `apply_theme(root)`
* **What to show & say:**
  > *"To ensure the app looks modern, all visual design rules are centralized here. We set the ttk theme to `'clam'`, define custom button states (`Accent.TButton` with `#2F5233` forest green and hover maps), and configure a consistent muted palette for subjects so that colors remain identical across the planner, timetable, and dashboard."*

---

### 2.4 The Decoupled Services Layer (Zero GUI Code)
* **Directory:** `services/`
* **Files:** 
  - `services/day_order.py` (Math for Day 1–5 working-day rotation)
  - `services/clash_detector.py` (Interval overlap algorithm)
  - `services/scheduler.py` (Urgency allocation & `reflow_on_missed`)
* **What to show & say:**
  > *"Notice that inside `services/`, there is **NOT A SINGLE IMPORT** of `tkinter`, `ttk`, or any GUI widget. Every function here takes raw data (lists, integers, strings), performs calculations, and returns data. Because of this architectural choice, our team was able to write 15 automated PyTest unit tests that run in milliseconds without launching windows."*

---

### 2.5 The Database Connection Factory & Foreign Keys
* **File:** `db/connection.py`
* **Key Function:** `get_connection(db_path=None)`
* **Code to point at:**
  ```python
  conn = sqlite3.connect(path)
  conn.row_factory = sqlite3.Row
  conn.execute("PRAGMA foreign_keys = ON;")
  ```
* **What to say:**
  > *"By default, SQLite disables foreign key validation. In our architecture, every connection explicitly executes `PRAGMA foreign_keys = ON;`. We also set `conn.row_factory = sqlite3.Row`, allowing queries to access columns by name like dictionaries, which prevents column-index bugs in the business logic."*

---

## 3. End-to-End Architectural Trace

When the examiner asks: *"Trace what happens architecturally when a student marks a session as missed"*:

```
[Step 1: User Action in GUI]
  User clicks "Mark Missed" in modal dialog on Weekly Planner
  (File: gui/screens/planner_screen.py)
         │
         ▼
[Step 2: Service Delegation]
  GUI calls services/scheduler.py -> reflow_on_missed(session_id, conn)
  (Notice: The GUI does NOT do the calculation itself!)
         │
         ▼
[Step 3: Database Update & Query]
  reflow_on_missed() calls db/queries.py -> update_study_session_status('missed')
  Clears future 'planned' sessions from today onward
  Queries remaining hours per topic from SQLite
         │
         ▼
[Step 4: Algorithm Re-Execution]
  Urgency formula is re-calculated for each topic
  get_free_slots() extracts open daytime slots
  build_schedule() greedily assigns remaining hours
  Inserts new planned sessions into StudySessions table
         │
         ▼
[Step 5: Event Notification & UI Refresh]
  Service returns {'success': True, 'reflowed_sessions_count': 14}
  GUI triggers self.refresh()
  Canvas redraws grid with updated cards and amber banner if slots are tight
```

---

## 4. Examiner Defense: Top 5 Tough Questions for Person A

### Q1: *"Why did you use a 3-tier architecture for a small desktop app? Isn't it overkill?"*
> **Answer:** *"No, professors, it is software engineering best practice. If we put SQLite queries inside Tkinter button handlers, changing the database or testing the scheduling algorithm would require modifying UI code. With our 3-tier structure:
> 1. Person B could write and test the clash and scheduler math in `services/` using `pytest` without waiting for the UI.
> 2. Person C could modify SQLite tables without breaking the frontend.
> 3. If tomorrow we want to migrate from Tkinter to a web interface or mobile app, the entire `services/` and `db/` layers remain 100% reusable."*

### Q2: *"How do your screens communicate with each other? If I add a class in the Timetable screen, how does the Clash Report or Sidebar know?"*
> **Answer:** *"Through callback hooks and active screen refreshing. In `gui/app.py`, we pass callback functions `on_data_change` and `on_clash_detected` to child screens. When a timetable slot is saved, it runs `_auto_rescan()`, updates the database, and invokes `self.on_clash_detected(count)`, which updates the sidebar warning badge immediately. Furthermore, whenever `show_screen()` switches tabs, it automatically invokes `target_screen.refresh()`."*

### Q3: *"What design pattern did you use in the database connection?"*
> **Answer:** *"The **Factory Pattern**. In `db/connection.py`, `get_connection()` abstracts connection creation, row factory configuration, and PRAGMA settings. This allows our unit test suite to pass `':memory:'` as the path for fast, isolated in-memory testing without touching the production `clashboard.db`."*

### Q4: *"What design pattern did you use for the GUI screens?"*
> **Answer:** *"A **Composite / Mediator Pattern**. The `ClashBoardApp` acts as the mediator holding the master state and sidebar. Individual screens are modular `ttk.Frame` composites that register with the mediator and respond to lifecycle events like `refresh()`."*

### Q5: *"Show me where the automated tests run."*
> **Action:** Open terminal and run:
> ```powershell
> python -m pytest -v
> ```
> **Say:** *"Notice test `test_gui_smoke.py`. It tests the entire architectural integration: initializes the database, starts the Tkinter root, iterates through all 5 screens, verifies widget rendering, and safely destroys the window. All 15 tests pass in 4 seconds."*
