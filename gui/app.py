"""
Main Application GUI Window for ClashBoard.
Enforces:
- Sidebar navigation on the left (NOT a top tab bar)
- Clam theme with #2F5233 accent and #F7F6F2 warm off-white background
- Segoe UI typography
- Seamless state synchronization across all 5 screens
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from db import queries
from db.seed import seed_database
from gui.styles import (
    apply_theme, BG_COLOR, SIDEBAR_BG, ACCENT_COLOR, TEXT_COLOR,
    MUTED_TEXT, BORDER_COLOR, STATUS_MISSED
)
from gui.screens import (
    PlannerScreen,
    TimetableScreen,
    ClashScreen,
    SubjectsScreen,
    DashboardScreen
)


class ClashBoardApp(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn

        self.title("ClashBoard — Timetable Clash Resolver & Adaptive Study Planner")
        self.geometry("1240x780")
        self.minsize(1024, 680)

        # Apply global theme
        self.style = apply_theme(self)

        self.active_nav_key = None
        self.nav_buttons = {}
        self.screens = {}

        self._build_layout()
        self._check_clash_badge()

        # Start on Weekly Planner (the main screen specified in spec)
        self.show_screen('planner')

    def _build_layout(self):
        # Master horizontal split: Left Sidebar, Right Main Content
        self.sidebar_frame = ttk.Frame(self, style='Sidebar.TFrame', width=240)
        self.sidebar_frame.pack(side='left', fill='y')
        self.sidebar_frame.pack_propagate(False)

        # Sidebar Separator line
        sep = tk.Frame(self, width=1, bg=BORDER_COLOR)
        sep.pack(side='left', fill='y')

        self.content_container = ttk.Frame(self, style='TFrame')
        self.content_container.pack(side='right', fill='both', expand=True)

        self._build_sidebar()
        self._init_screens()

    def _build_sidebar(self):
        # App branding header
        brand_box = tk.Frame(self.sidebar_frame, bg=SIDEBAR_BG, padx=16, pady=20)
        brand_box.pack(fill='x')

        lbl_logo = tk.Label(
            brand_box,
            text="🌿 ClashBoard",
            font=('Segoe UI', 16, 'bold'),
            fg=ACCENT_COLOR,
            bg=SIDEBAR_BG
        )
        lbl_logo.pack(anchor='w')

        lbl_tagline = tk.Label(
            brand_box,
            text="Adaptive Timetable & Study Engine",
            font=('Segoe UI', 8),
            fg=MUTED_TEXT,
            bg=SIDEBAR_BG
        )
        lbl_tagline.pack(anchor='w', pady=(2, 0))

        # Thin divider
        div = tk.Frame(self.sidebar_frame, height=1, bg=BORDER_COLOR)
        div.pack(fill='x', padx=14, pady=(0, 15))

        # Nav items
        nav_items = [
            ('planner', "📅  Weekly Planner"),
            ('timetable', "📋  Timetable & Exams"),
            ('clashes', "⚠️  Clash Report"),
            ('subjects', "📚  Subjects & Topics"),
            ('dashboard', "📊  Progress Dashboard"),
        ]

        nav_box = tk.Frame(self.sidebar_frame, bg=SIDEBAR_BG, padx=10)
        nav_box.pack(fill='x')

        for key, label in nav_items:
            btn = ttk.Button(
                nav_box,
                text=label,
                style='Nav.TButton',
                command=lambda k=key: self.show_screen(k)
            )
            btn.pack(fill='x', pady=4)
            self.nav_buttons[key] = btn

        # Spacer to push bottom status box down
        spacer = tk.Frame(self.sidebar_frame, bg=SIDEBAR_BG)
        spacer.pack(fill='both', expand=True)

        # Bottom info card
        bottom_card = tk.Frame(self.sidebar_frame, bg='#DFDCD3', padx=12, pady=12)
        bottom_card.pack(fill='x', padx=12, pady=16)

        today_str = datetime.date.today().strftime("%a, %b %d, %Y")
        lbl_date = tk.Label(
            bottom_card,
            text=f"Today: {today_str}",
            font=('Segoe UI', 8, 'bold'),
            fg=TEXT_COLOR,
            bg='#DFDCD3'
        )
        lbl_date.pack(anchor='w')

        self.lbl_sidebar_status = tk.Label(
            bottom_card,
            text="System Ready",
            font=('Segoe UI', 8),
            fg=ACCENT_COLOR,
            bg='#DFDCD3'
        )
        self.lbl_sidebar_status.pack(anchor='w', pady=(2, 8))

        btn_reset = ttk.Button(
            bottom_card,
            text="Reset Demo Seed Data",
            style='Secondary.TButton',
            command=self._reset_seed_data
        )
        btn_reset.pack(fill='x')

    def _init_screens(self):
        """Instantiates all 5 screen frames."""
        self.screens['planner'] = PlannerScreen(
            self.content_container,
            self.conn,
            on_data_change=self._on_data_updated
        )
        self.screens['timetable'] = TimetableScreen(
            self.content_container,
            self.conn,
            on_clash_detected=self._on_clashes_detected
        )
        self.screens['clashes'] = ClashScreen(
            self.content_container,
            self.conn,
            on_clash_update=self._on_clashes_detected
        )
        self.screens['subjects'] = SubjectsScreen(
            self.content_container,
            self.conn,
            on_data_change=self._on_data_updated
        )
        self.screens['dashboard'] = DashboardScreen(
            self.content_container,
            self.conn
        )

    def show_screen(self, screen_key):
        """Switches visible screen and updates navigation button styling."""
        if self.active_nav_key == screen_key:
            return

        # Hide currently active screen
        if self.active_nav_key and self.active_nav_key in self.screens:
            self.screens[self.active_nav_key].pack_forget()
            if self.active_nav_key in self.nav_buttons:
                self.nav_buttons[self.active_nav_key].configure(style='Nav.TButton')

        # Show target screen
        self.active_nav_key = screen_key
        target_screen = self.screens[screen_key]
        target_screen.pack(fill='both', expand=True)

        if screen_key in self.nav_buttons:
            self.nav_buttons[screen_key].configure(style='NavActive.TButton')

        # Always trigger fresh refresh
        if hasattr(target_screen, 'refresh'):
            target_screen.refresh()

        self._check_clash_badge()

    def _on_data_updated(self):
        """Called whenever data is modified in planner or subjects."""
        self._check_clash_badge()
        # If dashboard exists, refresh it
        if 'dashboard' in self.screens and hasattr(self.screens['dashboard'], 'refresh'):
            self.screens['dashboard'].refresh()
        if 'planner' in self.screens and self.active_nav_key != 'planner':
            self.screens['planner'].refresh()

    def _on_clashes_detected(self, clash_count):
        """Updates clash badge and status."""
        self._check_clash_badge(clash_count)
        if 'dashboard' in self.screens:
            self.screens['dashboard'].refresh()

    def _check_clash_badge(self, clash_count=None):
        if clash_count is None:
            clashes = queries.get_all_clashes(self.conn)
            clash_count = len(clashes)

        clash_btn = self.nav_buttons.get('clashes')
        if clash_btn:
            if clash_count > 0:
                clash_btn.configure(text=f"⚠️  Clash Report ({clash_count})")
                self.lbl_sidebar_status.config(
                    text=f"⚠️ {clash_count} conflict(s) detected!",
                    fg=STATUS_MISSED
                )
            else:
                clash_btn.configure(text="✓  Clash Report (0)")
                self.lbl_sidebar_status.config(
                    text="✓ Zero Conflicts",
                    fg=ACCENT_COLOR
                )

    def _reset_seed_data(self):
        if messagebox.askyesno(
            "Confirm Reset",
            "This will clear the current database and restore realistic demo data\n"
            "(6 subjects, ~15 timetable slots, 4 exams, 20 topics, sample clashes and plan).\n\n"
            "Proceed with reset?"
        ):
            seed_database(self.conn, force=True)
            self._check_clash_badge()
            for scr in self.screens.values():
                if hasattr(scr, 'refresh'):
                    scr.refresh()
            if hasattr(self.screens['subjects'], 'refresh_subjects'):
                self.screens['subjects'].refresh_subjects()
            messagebox.showinfo("Reset Complete", "Demo seed data successfully restored!")

