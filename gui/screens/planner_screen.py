"""
Weekly Planner Screen for ClashBoard (Main Screen).
Canvas-drawn 7-day grid showing:
- Classes from weekly timetable (subtle background blocks)
- Study sessions color-coded by subject with planned/done/missed statuses
- Clickable session cards to mark Done or Missed (triggers reflow_on_missed)
- Week navigation (Prev, Today, Next)
- Unscheduled topics warning banner
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from db import queries
from services.clash_detector import time_to_minutes
from services.scheduler import get_free_slots, build_schedule, reflow_on_missed
from gui.styles import (
    BG_COLOR, CARD_BG, ACCENT_COLOR, TEXT_COLOR, MUTED_TEXT,
    BORDER_COLOR, STATUS_DONE, STATUS_MISSED, STATUS_PLANNED,
    STATUS_WARNING, get_subject_colors
)


class PlannerScreen(ttk.Frame):
    def __init__(self, parent, conn, on_data_change=None):
        super().__init__(parent, style='TFrame')
        self.conn = conn
        self.on_data_change = on_data_change

        # Current view week starting on Monday
        today = datetime.date.today()
        self.current_monday = today - datetime.timedelta(days=today.weekday())

        self.session_card_map = {}  # canvas_tag -> session_dict
        self.unscheduled_topics = []

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self, style='TFrame')
        toolbar.pack(fill='x', padx=20, pady=(15, 8))

        # Left: Title and week navigation
        nav_box = ttk.Frame(toolbar, style='TFrame')
        nav_box.pack(side='left', fill='y')

        ttk.Label(nav_box, text="Weekly Study Planner", style='Header.TLabel').pack(side='left', padx=(0, 15))

        btn_prev = ttk.Button(nav_box, text="◀ Prev", style='Secondary.TButton', command=self._prev_week)
        btn_prev.pack(side='left', padx=2)

        btn_today = ttk.Button(nav_box, text="Current Week", style='Secondary.TButton', command=self._this_week)
        btn_today.pack(side='left', padx=2)

        btn_next = ttk.Button(nav_box, text="Next ▶", style='Secondary.TButton', command=self._next_week)
        btn_next.pack(side='left', padx=2)

        self.lbl_week_range = ttk.Label(nav_box, text="", font=('Segoe UI', 10, 'bold'), foreground=TEXT_COLOR)
        self.lbl_week_range.pack(side='left', padx=(12, 0))

        # Right: Action buttons
        actions_box = ttk.Frame(toolbar, style='TFrame')
        actions_box.pack(side='right')

        btn_generate = ttk.Button(
            actions_box,
            text="⚡ Auto-Generate Study Plan",
            style='Accent.TButton',
            command=self._generate_plan_dialog
        )
        btn_generate.pack(side='right', padx=4)

        # Warning banner for unscheduled topics
        self.banner_frame = tk.Frame(self, bg='#FDF2E9', relief='solid', borderwidth=1, highlightbackground=STATUS_WARNING)
        self.lbl_banner = tk.Label(
            self.banner_frame,
            text="",
            font=('Segoe UI', 9, 'bold'),
            fg='#8A4206',
            bg='#FDF2E9',
            justify='left'
        )
        self.lbl_banner.pack(side='left', padx=12, pady=6)
        # Not packed initially, packed when unscheduled topics exist

        # Subject Palette Legend Bar
        self.legend_frame = ttk.Frame(self, style='TFrame')
        self.legend_frame.pack(fill='x', padx=20, pady=(0, 6))

        # Canvas container with vertical scrollbar
        grid_container = ttk.Frame(self, style='TFrame')
        grid_container.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        self.canvas = tk.Canvas(grid_container, bg=BG_COLOR, highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.v_scrollbar = ttk.Scrollbar(grid_container, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        self.v_scrollbar.pack(side='right', fill='y')

        # Bind resize and canvas clicks
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind('<Button-1>', self._on_canvas_click)

        # Mouse wheel scrolling
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

    def _on_mousewheel(self, event):
        # Only scroll if this screen is visible
        if self.winfo_viewable():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _prev_week(self):
        self.current_monday -= datetime.timedelta(days=7)
        self.refresh()

    def _next_week(self):
        self.current_monday += datetime.timedelta(days=7)
        self.refresh()

    def _this_week(self):
        today = datetime.date.today()
        self.current_monday = today - datetime.timedelta(days=today.weekday())
        self.refresh()

    def _on_canvas_configure(self, event):
        self.draw_grid()

    def refresh(self):
        """Refreshes week header, legend, and redraws the grid."""
        sunday = self.current_monday + datetime.timedelta(days=6)
        self.lbl_week_range.config(
            text=f"{self.current_monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')}"
        )
        self._refresh_legend()
        self.draw_grid()

    def _refresh_legend(self):
        # Clear existing legend items
        for widget in self.legend_frame.winfo_children():
            widget.destroy()

        ttk.Label(self.legend_frame, text="Subjects:", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 8))

        subjects = queries.get_all_subjects(self.conn)
        for s in subjects:
            border_c, fill_c = get_subject_colors(s['subject_id'])
            item_f = ttk.Frame(self.legend_frame, style='TFrame')
            item_f.pack(side='left', padx=6)

            swatch = tk.Canvas(item_f, width=12, height=12, bg=border_c, highlightthickness=0)
            swatch.pack(side='left', padx=(0, 4))

            lbl = ttk.Label(item_f, text=s['code'] or s['name'], font=('Segoe UI', 8))
            lbl.pack(side='left')

    def draw_grid(self):
        """Draws the 7-day grid and plots timetable classes & study sessions."""
        self.canvas.delete('all')
        self.session_card_map.clear()

        width = self.canvas.winfo_width()
        if width <= 100:
            width = 960  # Default fallback width before geometry manager stabilizes

        # Grid metrics
        time_col_w = 60
        header_h = 44
        total_days = 7
        day_col_w = (width - time_col_w) / total_days

        # Time range: 07:00 (420) to 23:00 (1380) = 16 hours
        start_hour = 7
        end_hour = 23
        total_hours = end_hour - start_hour
        hour_h = 52
        grid_h = header_h + (total_hours * hour_h)

        # Configure scrollregion
        self.canvas.configure(scrollregion=(0, 0, width, grid_h + 20))

        # Background headers
        self.canvas.create_rectangle(0, 0, width, header_h, fill='#EDECE6', outline=BORDER_COLOR)

        days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        week_dates = [self.current_monday + datetime.timedelta(days=i) for i in range(7)]
        today = datetime.date.today()

        # Draw Day Columns and Headers
        for i in range(total_days):
            x1 = time_col_w + i * day_col_w
            x2 = x1 + day_col_w
            dt = week_dates[i]
            is_today = (dt == today)

            # Header cell
            header_bg = '#DDE4DC' if is_today else '#EDECE6'
            self.canvas.create_rectangle(x1, 0, x2, header_h, fill=header_bg, outline=BORDER_COLOR)

            day_text = f"{days_of_week[i]} {dt.strftime('%d %b')}"
            header_font = ('Segoe UI', 9, 'bold' if is_today else 'normal')
            header_fg = ACCENT_COLOR if is_today else TEXT_COLOR
            self.canvas.create_text((x1 + x2) / 2, header_h / 2, text=day_text, font=header_font, fill=header_fg)

            # Day column background
            col_bg = '#FBFBF9' if i % 2 == 0 else '#F7F6F2'
            self.canvas.create_rectangle(x1, header_h, x2, grid_h, fill=col_bg, outline=BORDER_COLOR)

        # Draw Hour Rows & Time Labels
        for h in range(start_hour, end_hour + 1):
            y = header_h + (h - start_hour) * hour_h
            time_str = f"{h:02d}:00"

            # Label on time column
            self.canvas.create_text(time_col_w / 2, y, text=time_str, font=('Segoe UI', 8), fill=MUTED_TEXT)
            # Grid line
            self.canvas.create_line(time_col_w, y, width, y, fill='#E5E3DB', dash=(2, 4) if h != start_hour else ())

        # --- 1. DRAW TIMETABLE CLASSES (Background blocks) ---
        timetable_slots = queries.get_all_timetable_slots(self.conn)
        for s in timetable_slots:
            day_name = s.get('day_of_week', '').capitalize()[:3]
            if day_name not in days_of_week:
                continue
            day_idx = days_of_week.index(day_name)

            s_min = time_to_minutes(s['start_time'])
            e_min = time_to_minutes(s['end_time'])
            
            # Map minutes to Y
            y1 = header_h + ((s_min - (start_hour * 60)) / 60.0) * hour_h
            y2 = header_h + ((e_min - (start_hour * 60)) / 60.0) * hour_h
            x1 = time_col_w + day_idx * day_col_w + 3
            x2 = x1 + day_col_w - 6

            if y2 > header_h and y1 < grid_h:
                y1_clamp = max(y1, header_h)
                y2_clamp = min(y2, grid_h)

                # Class background card (subtle hatching/dash)
                self.canvas.create_rectangle(
                    x1, y1_clamp, x2, y2_clamp,
                    fill='#EBE8DF',
                    outline='#BEBBAF',
                    dash=(3, 3)
                )
                title = f"🏛 {s.get('subject_code', '')} {s.get('section', '')}"
                self.canvas.create_text(
                    x1 + 6, y1_clamp + 8,
                    text=title,
                    anchor='nw',
                    font=('Segoe UI', 8, 'italic'),
                    fill='#555555'
                )

        # --- 2. DRAW EXAMS (If any in this week) ---
        all_exams = queries.get_all_exams(self.conn)
        for ex in all_exams:
            ex_date_str = ex.get('exam_date')
            for day_idx, dt in enumerate(week_dates):
                if dt.strftime('%Y-%m-%d') == ex_date_str:
                    s_min = time_to_minutes(ex['start_time'])
                    e_min = time_to_minutes(ex['end_time'])
                    y1 = header_h + ((s_min - (start_hour * 60)) / 60.0) * hour_h
                    y2 = header_h + ((e_min - (start_hour * 60)) / 60.0) * hour_h
                    x1 = time_col_w + day_idx * day_col_w + 3
                    x2 = x1 + day_col_w - 6

                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill='#FADBD8',
                        outline=STATUS_MISSED,
                        width=2
                    )
                    self.canvas.create_text(
                        x1 + 6, y1 + 6,
                        text=f"⚠️ EXAM: {ex.get('subject_code', '')}",
                        anchor='nw',
                        font=('Segoe UI', 8, 'bold'),
                        fill='#78281F'
                    )

        # --- 3. DRAW STUDY SESSIONS ---
        start_date_str = self.current_monday.strftime('%Y-%m-%d')
        end_date_str = (self.current_monday + datetime.timedelta(days=6)).strftime('%Y-%m-%d')
        sessions = queries.get_study_sessions_by_date_range(self.conn, start_date_str, end_date_str)

        for sess in sessions:
            sess_dt_str = sess.get('scheduled_date')
            try:
                sess_dt = datetime.date.fromisoformat(sess_dt_str)
                day_idx = (sess_dt - self.current_monday).days
            except Exception:
                continue

            if 0 <= day_idx < 7:
                s_min = time_to_minutes(sess['scheduled_start'])
                e_min = time_to_minutes(sess['scheduled_end'])

                y1 = header_h + ((s_min - (start_hour * 60)) / 60.0) * hour_h
                y2 = header_h + ((e_min - (start_hour * 60)) / 60.0) * hour_h
                x1 = time_col_w + day_idx * day_col_w + 4
                x2 = x1 + day_col_w - 8

                border_color, fill_color = get_subject_colors(sess.get('subject_id', 0))
                status = sess.get('status', 'planned')

                # Card tag for click detection
                tag = f"sess_{sess['session_id']}"
                self.session_card_map[tag] = sess

                # Status modifications
                status_icon = "⏳"
                if status == 'done':
                    status_icon = "✓"
                    border_color = STATUS_DONE
                    fill_color = '#EAF2E8'
                elif status == 'missed':
                    status_icon = "✕"
                    border_color = STATUS_MISSED
                    fill_color = '#FDEDEC'

                # Draw Card Rect
                card_id = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=fill_color,
                    outline=border_color,
                    width=2,
                    tags=(tag, 'session_card')
                )

                # Header text: [Status] Subject Code
                header_text = f"{status_icon} {sess.get('subject_code', '')} {sess.get('scheduled_start')}-{sess.get('scheduled_end')}"
                self.canvas.create_text(
                    x1 + 6, y1 + 5,
                    text=header_text,
                    anchor='nw',
                    font=('Segoe UI', 8, 'bold'),
                    fill=border_color,
                    tags=(tag, 'session_text')
                )

                # Topic name text
                # Truncate if long
                card_w_chars = int((x2 - x1) / 7)
                topic_title = sess.get('topic_name', '')
                if len(topic_title) > card_w_chars:
                    topic_title = topic_title[:card_w_chars - 3] + "..."

                self.canvas.create_text(
                    x1 + 6, y1 + 20,
                    text=topic_title,
                    anchor='nw',
                    font=('Segoe UI', 8),
                    fill=TEXT_COLOR,
                    tags=(tag, 'session_text')
                )

    def _on_canvas_click(self, event):
        """Detects clicks on study session cards and opens the action modal."""
        # Adjust for canvas scrolling
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        clicked_items = self.canvas.find_overlapping(cx - 1, cy - 1, cx + 1, cy + 1)

        for item in clicked_items:
            tags = self.canvas.gettags(item)
            for t in tags:
                if t in self.session_card_map:
                    session = self.session_card_map[t]
                    self._open_session_modal(session)
                    return

    def _open_session_modal(self, session):
        """Displays interactive action dialog to mark Done or Missed (reflow)."""
        modal = tk.Toplevel(self)
        modal.title(f"Study Session #{session['session_id']}")
        modal.geometry("450x330")
        modal.configure(bg=BG_COLOR)
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        # Center dialog
        modal.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 225
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 165
        modal.geometry(f"+{x}+{y}")

        content = ttk.Frame(modal, style='TFrame', padding=20)
        content.pack(fill='both', expand=True)

        ttk.Label(
            content,
            text=f"Session: {session.get('subject_code', '')} — {session.get('subject_name', '')}",
            style='Header.TLabel'
        ).pack(anchor='w', pady=(0, 4))

        ttk.Label(
            content,
            text=f"Topic: {session.get('topic_name', '')}",
            font=('Segoe UI', 11, 'bold'),
            foreground=TEXT_COLOR
        ).pack(anchor='w', pady=(0, 6))

        info_box = ttk.LabelFrame(content, text=" Session Details ", padding=10)
        info_box.pack(fill='x', pady=6)

        dt_info = f"📅 Date: {session.get('scheduled_date')}  |  🕒 {session.get('scheduled_start')} – {session.get('scheduled_end')}"
        ttk.Label(info_box, text=dt_info).pack(anchor='w', pady=2)

        cur_status = session.get('status', 'planned').upper()
        status_color = STATUS_DONE if cur_status == 'DONE' else (STATUS_MISSED if cur_status == 'MISSED' else ACCENT_COLOR)
        lbl_st = tk.Label(
            info_box,
            text=f"Current Status: {cur_status}",
            font=('Segoe UI', 10, 'bold'),
            fg=status_color,
            bg=BG_COLOR
        )
        lbl_st.pack(anchor='w', pady=2)

        # Action Buttons
        btn_box = ttk.Frame(content, style='TFrame')
        btn_box.pack(fill='x', pady=(15, 0))

        def on_done():
            queries.update_study_session_status(self.conn, session['session_id'], 'done')
            modal.destroy()
            self.refresh()
            if self.on_data_change:
                self.on_data_change()

        def on_missed():
            # Trigger automatic reflow!
            res = reflow_on_missed(session['session_id'], self.conn)
            modal.destroy()
            self.refresh()
            if self.on_data_change:
                self.on_data_change()

            # Surface reflow result notification
            cnt = res.get('reflowed_sessions_count', 0)
            unsched = res.get('unscheduled_topics', [])
            self.unscheduled_topics = unsched
            self._update_banner(unsched)

            msg = f"Session marked as Missed.\nSuccessfully reflowed {cnt} remaining study session(s)!"
            if unsched:
                msg += f"\n\n⚠️ Note: {len(unsched)} topic(s) could not be fully scheduled before upcoming exams."
            messagebox.showinfo("Adaptive Reflow Complete", msg)

        def on_delete():
            if messagebox.askyesno("Confirm Delete", "Delete this scheduled study session?"):
                queries.delete_study_session(self.conn, session['session_id'])
                modal.destroy()
                self.refresh()
                if self.on_data_change:
                    self.on_data_change()

        btn_done = ttk.Button(btn_box, text="✓ Mark as Done", style='Accent.TButton', command=on_done)
        btn_done.pack(side='left', padx=3)

        btn_missed = ttk.Button(btn_box, text="✕ Mark Missed (Auto-Reflow)", style='Danger.TButton', command=on_missed)
        btn_missed.pack(side='left', padx=3)

        btn_del = ttk.Button(btn_box, text="Delete", style='Secondary.TButton', command=on_delete)
        btn_del.pack(side='left', padx=3)

    def _update_banner(self, unscheduled):
        if not unscheduled:
            self.banner_frame.pack_forget()
        else:
            names = ", ".join([f"{u['subject_name']}: {u['topic_name']} ({u['unallocated_hours']}h left)" for u in unscheduled[:2]])
            if len(unscheduled) > 2:
                names += f" and {len(unscheduled) - 2} more"
            self.lbl_banner.config(
                text=f"⚠️ Insufficient free slots before exams: {names}."
            )
            self.banner_frame.pack(fill='x', padx=20, pady=(0, 6), before=self.legend_frame)

    def _generate_plan_dialog(self):
        """Generates or rebuilds the entire study plan from scratch across available free time."""
        if messagebox.askyesno(
            "Generate Study Plan",
            "This will calculate topic urgencies and schedule study sessions across your free time.\n"
            "Existing 'planned' sessions will be replaced. 'Done' sessions will be preserved.\n\n"
            "Proceed?"
        ):
            self.rebuild_study_plan()

    def rebuild_study_plan(self):
        """Runs the pure scheduler and saves generated sessions to DB."""
        today = datetime.date.today()
        # 1. Clear planned sessions from today onwards
        queries.clear_planned_study_sessions(self.conn, from_date=today.strftime('%Y-%m-%d'))

        # 2. Get topics and remaining hours
        all_topics = queries.get_all_topics(self.conn)
        timetable_slots = queries.get_all_timetable_slots(self.conn)
        exams = queries.get_all_exams(self.conn)

        # Get completed hours per topic
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT topic_id, 
                   SUM((strftime('%s', '2000-01-01 ' || scheduled_end) - 
                        strftime('%s', '2000-01-01 ' || scheduled_start)) / 3600.0) AS done_hrs
            FROM StudySessions
            WHERE status = 'done'
            GROUP BY topic_id
        """)
        done_map = {row['topic_id']: (row['done_hrs'] or 0.0) for row in cursor.fetchall()}

        topics_to_schedule = []
        for t in all_topics:
            done_hrs = done_map.get(t['topic_id'], 0.0)
            rem = max(0.0, round(float(t['estimated_hours']) - done_hrs, 2))
            if rem > 0:
                t_dict = dict(t)
                t_dict['estimated_hours'] = rem
                topics_to_schedule.append(t_dict)

        # 3. Generate free slots for the next 21 days
        planning_days = [today + datetime.timedelta(days=i) for i in range(21)]
        free_slots = get_free_slots(timetable_slots, planning_days, exams=exams)

        # 4. Run scheduler
        plan_result = build_schedule(topics_to_schedule, free_slots, reference_date=today)

        # 5. Insert new planned sessions
        with self.conn:
            for s in plan_result['sessions']:
                queries.insert_study_session(
                    self.conn,
                    topic_id=s['topic_id'],
                    scheduled_date=s['scheduled_date'],
                    scheduled_start=s['scheduled_start'],
                    scheduled_end=s['scheduled_end'],
                    status='planned'
                )

        self.unscheduled_topics = plan_result['unscheduled_topics']
        self._update_banner(self.unscheduled_topics)
        self.refresh()
        if self.on_data_change:
            self.on_data_change()

        cnt = len(plan_result['sessions'])
        msg = f"Schedule generated successfully! Created {cnt} study sessions."
        if self.unscheduled_topics:
            msg += f"\n\n⚠️ {len(self.unscheduled_topics)} topic(s) had insufficient time before their exam dates."
        messagebox.showinfo("Planner", msg)

