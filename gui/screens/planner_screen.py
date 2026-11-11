"""
Weekly Planner Screen for ClashBoard.

Canvas-drawn 7-day calendar with:
  • Day headers showing BOTH weekday (Mon/Tue/…) and Day Order (DO1–DO5)
  • Timetable class blocks rendered for the Day Order of each calendar day
  • Study session cards, colour-coded by subject, click to mark Done/Missed
  • Missed → triggers reflow_on_missed and immediately redraws the grid
  • Week navigation + Auto-Generate Study Plan button
  • Day Order Pivot configurator so the DO↔weekday mapping can be adjusted
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
from db import queries
from services.clash_detector import time_to_minutes
from services.scheduler import get_free_slots, build_schedule, reflow_on_missed
from services.day_order import get_day_order, day_order_label
from gui.styles import (
    BG_COLOR, CARD_BG, ACCENT_COLOR, TEXT_COLOR, MUTED_TEXT,
    BORDER_COLOR, STATUS_DONE, STATUS_MISSED, STATUS_PLANNED,
    STATUS_WARNING, get_subject_colors,
)

DAYS_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


class PlannerScreen(ttk.Frame):
    def __init__(self, parent, conn, on_data_change=None):
        super().__init__(parent, style='TFrame')
        self.conn            = conn
        self.on_data_change  = on_data_change
        self.session_card_map: dict[str, dict] = {}
        self.unscheduled_topics: list = []

        today = datetime.date.today()
        self.current_monday = today - datetime.timedelta(days=today.weekday())

        self._build_ui()
        self.refresh()

    # ═══════════════════════════════════════════════════════════════════════
    # Layout
    # ═══════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self, style='TFrame')
        toolbar.pack(fill='x', padx=20, pady=(15, 8))

        nav = ttk.Frame(toolbar, style='TFrame')
        nav.pack(side='left')

        ttk.Label(nav, text="Weekly Study Planner", style='Header.TLabel').pack(side='left', padx=(0, 15))
        ttk.Button(nav, text="◀ Prev",        style='Secondary.TButton', command=self._prev_week).pack(side='left', padx=2)
        ttk.Button(nav, text="Current Week",  style='Secondary.TButton', command=self._this_week).pack(side='left', padx=2)
        ttk.Button(nav, text="Next ▶",        style='Secondary.TButton', command=self._next_week).pack(side='left', padx=2)

        self.lbl_week = ttk.Label(nav, text="", font=('Segoe UI', 10, 'bold'), foreground=TEXT_COLOR)
        self.lbl_week.pack(side='left', padx=(12, 0))

        actions = ttk.Frame(toolbar, style='TFrame')
        actions.pack(side='right')
        ttk.Button(actions, text="🗓 Set Day Order Pivot", style='Secondary.TButton',
                   command=self._configure_pivot).pack(side='right', padx=4)
        ttk.Button(actions, text="⚡ Auto-Generate Study Plan", style='Accent.TButton',
                   command=self._generate_plan_dialog).pack(side='right', padx=4)

        # Pivot info bar
        self.lbl_pivot_info = ttk.Label(
            self, text="", font=('Segoe UI', 9, 'italic'), foreground=MUTED_TEXT
        )
        self.lbl_pivot_info.pack(fill='x', padx=20, pady=(0, 4))

        # Warning banner (unscheduled topics)
        self.banner_frame = tk.Frame(self, bg='#FDF2E9', relief='solid',
                                     borderwidth=1, highlightbackground=STATUS_WARNING)
        self.lbl_banner = tk.Label(self.banner_frame, text="", font=('Segoe UI', 9, 'bold'),
                                   fg='#8A4206', bg='#FDF2E9', justify='left')
        self.lbl_banner.pack(side='left', padx=12, pady=6)

        # Subject palette legend
        self.legend_frame = ttk.Frame(self, style='TFrame')
        self.legend_frame.pack(fill='x', padx=20, pady=(0, 4))

        # Canvas + scrollbar
        grid_ctr = ttk.Frame(self, style='TFrame')
        grid_ctr.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        self.canvas = tk.Canvas(grid_ctr, bg=BG_COLOR,
                                highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.vscroll = ttk.Scrollbar(grid_ctr, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.vscroll.pack(side='right', fill='y')

        self.canvas.bind('<Configure>', lambda e: self.draw_grid())
        self.canvas.bind('<Button-1>',  self._on_canvas_click)
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

    # ═══════════════════════════════════════════════════════════════════════
    # Week navigation
    # ═══════════════════════════════════════════════════════════════════════

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

    def _on_mousewheel(self, event):
        if self.winfo_viewable():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ═══════════════════════════════════════════════════════════════════════
    # Pivot configuration dialog
    # ═══════════════════════════════════════════════════════════════════════

    def _configure_pivot(self):
        """Let the user set which date and Day Order to use as the mapping anchor."""
        dlg = tk.Toplevel(self)
        dlg.title("Configure Day Order Pivot")
        dlg.geometry("380x200")
        dlg.configure(bg=BG_COLOR)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        pad = ttk.Frame(dlg, style='TFrame', padding=20)
        pad.pack(fill='both', expand=True)

        current_pivot = queries.get_setting(self.conn, 'pivot_date') or ''
        current_do    = queries.get_setting(self.conn, 'pivot_day_order') or '1'

        ttk.Label(pad, text="Reference Date (YYYY-MM-DD):", style='TLabel').grid(row=0, column=0, sticky='w', pady=6)
        entry_date = ttk.Entry(pad, width=18)
        entry_date.insert(0, current_pivot)
        entry_date.grid(row=0, column=1, padx=8, pady=6)

        ttk.Label(pad, text="Day Order on that date:", style='TLabel').grid(row=1, column=0, sticky='w', pady=6)
        cb_do = ttk.Combobox(pad, values=["Day 1","Day 2","Day 3","Day 4","Day 5"], state='readonly', width=12)
        cb_do.set(f"Day {current_do}")
        cb_do.grid(row=1, column=1, padx=8, pady=6)

        ttk.Label(pad, text="(Sets the anchor for all Day Order calculations)",
                  style='Muted.TLabel').grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 8))

        def save():
            date_str = entry_date.get().strip()
            do_str   = cb_do.get()
            do_num   = int(do_str.split()[-1]) if do_str else 1
            try:
                datetime.date.fromisoformat(date_str)
            except ValueError:
                messagebox.showwarning("Invalid Date", "Enter date as YYYY-MM-DD", parent=dlg)
                return
            queries.set_setting(self.conn, 'pivot_date',       date_str)
            queries.set_setting(self.conn, 'pivot_day_order',  str(do_num))
            dlg.destroy()
            self.refresh()

        ttk.Button(pad, text="Save", style='Accent.TButton', command=save).grid(
            row=3, column=0, columnspan=2, pady=(8, 0))

    # ═══════════════════════════════════════════════════════════════════════
    # Refresh entry point
    # ═══════════════════════════════════════════════════════════════════════

    def refresh(self):
        self.pivot_date = queries.get_setting(self.conn, 'pivot_date')
        self.pivot_do   = int(queries.get_setting(self.conn, 'pivot_day_order', '1'))

        sunday = self.current_monday + datetime.timedelta(days=6)
        self.lbl_week.config(
            text=f"{self.current_monday.strftime('%b %d')} – {sunday.strftime('%b %d, %Y')}"
        )
        self.lbl_pivot_info.config(
            text=f"Day Order Pivot: {self.pivot_date}  = Day {self.pivot_do}  "
                 f"(Day 1 = Mon, Day 2 = Tue … by default)"
        )
        self._refresh_legend()
        self.draw_grid()

    def _refresh_legend(self):
        for w in self.legend_frame.winfo_children():
            w.destroy()
        ttk.Label(self.legend_frame, text="Subjects:", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 8))
        for s in queries.get_all_subjects(self.conn):
            bc, fc = get_subject_colors(s['subject_id'])
            f = ttk.Frame(self.legend_frame, style='TFrame')
            f.pack(side='left', padx=5)
            tk.Canvas(f, width=12, height=12, bg=bc, highlightthickness=0).pack(side='left', padx=(0, 3))
            ttk.Label(f, text=s['code'] or s['name'], font=('Segoe UI', 8)).pack(side='left')

    # ═══════════════════════════════════════════════════════════════════════
    # Canvas grid drawing
    # ═══════════════════════════════════════════════════════════════════════

    def draw_grid(self):
        self.canvas.delete('all')
        self.session_card_map.clear()

        width = self.canvas.winfo_width() or 980

        # Grid metrics
        time_col_w  = 64
        header_h    = 54            # taller header to show DO + weekday
        total_days  = 7
        day_col_w   = (width - time_col_w) / total_days

        # Visible time range: 07:00–17:30 (covers all class periods + early study)
        # For evening study sessions the scrollbar allows seeing further
        start_hour  = 7
        end_hour    = 23
        total_hours = end_hour - start_hour
        hour_h      = 54
        grid_h      = header_h + total_hours * hour_h

        self.canvas.configure(scrollregion=(0, 0, width, grid_h + 20))

        week_dates = [self.current_monday + datetime.timedelta(days=i) for i in range(7)]
        today      = datetime.date.today()

        # ── Background header strip ──────────────────────────────────────
        self.canvas.create_rectangle(0, 0, width, header_h, fill='#EDECE6', outline=BORDER_COLOR)

        # ── Day columns ──────────────────────────────────────────────────
        for idx, dt in enumerate(week_dates):
            x1 = time_col_w + idx * day_col_w
            x2 = x1 + day_col_w
            is_today  = (dt == today)
            is_wkend  = (dt.weekday() >= 5)
            day_order = get_day_order(dt, self.pivot_date, self.pivot_do) if not is_wkend else None

            # Header cell
            hdr_bg = '#DDE4DC' if is_today else ('#EAEAE6' if is_wkend else '#EDECE6')
            self.canvas.create_rectangle(x1, 0, x2, header_h, fill=hdr_bg, outline=BORDER_COLOR)

            # Weekday label (always shown)
            weekday_txt = dt.strftime('%a %d %b')
            hdr_font    = ('Segoe UI', 9, 'bold' if is_today else 'normal')
            hdr_fg      = ACCENT_COLOR if is_today else (MUTED_TEXT if is_wkend else TEXT_COLOR)
            self.canvas.create_text((x1 + x2) / 2, header_h * 0.32,
                                    text=weekday_txt, font=hdr_font, fill=hdr_fg)

            # Day Order badge  (only on weekdays)
            if day_order:
                do_txt  = f"Day {day_order}"
                do_bg   = ACCENT_COLOR if is_today else '#7A9A78'
                do_x1   = (x1 + x2) / 2 - 22
                do_x2   = (x1 + x2) / 2 + 22
                do_y1   = header_h * 0.58
                do_y2   = header_h * 0.90
                self.canvas.create_rectangle(do_x1, do_y1, do_x2, do_y2,
                                             fill=do_bg, outline='', width=0)
                self.canvas.create_text((x1 + x2) / 2, (do_y1 + do_y2) / 2,
                                        text=do_txt, font=('Segoe UI', 8, 'bold'), fill='white')
            else:
                # Weekend indicator
                self.canvas.create_text((x1 + x2) / 2, header_h * 0.72,
                                        text="Weekend", font=('Segoe UI', 7, 'italic'), fill=MUTED_TEXT)

            # Column background
            col_bg = '#F3F2EF' if is_wkend else ('#FBFBF9' if idx % 2 == 0 else '#F7F6F2')
            self.canvas.create_rectangle(x1, header_h, x2, grid_h, fill=col_bg, outline=BORDER_COLOR)

        # ── Time axis ────────────────────────────────────────────────────
        for h in range(start_hour, end_hour + 1):
            y   = header_h + (h - start_hour) * hour_h
            lbl = f"{h:02d}:00"
            self.canvas.create_text(time_col_w / 2, y, text=lbl,
                                    font=('Segoe UI', 8), fill=MUTED_TEXT)
            self.canvas.create_line(time_col_w, y, width, y,
                                    fill='#E5E3DB', dash=(2, 4) if h != start_hour else ())

        # Pre-load timetable by day_order
        all_slots = queries.get_all_timetable_slots(self.conn)
        slots_by_do: dict[int, list] = {}
        for s in all_slots:
            slots_by_do.setdefault(int(s['day_order']), []).append(s)

        # Pre-load exams
        all_exams = queries.get_all_exams(self.conn)

        # ── Draw timetable class blocks ───────────────────────────────────
        for idx, dt in enumerate(week_dates):
            if dt.weekday() >= 5:
                continue
            day_order = get_day_order(dt, self.pivot_date, self.pivot_do)
            if not day_order:
                continue

            for s in slots_by_do.get(day_order, []):
                self._draw_class_block(s, idx, day_col_w, time_col_w, header_h, start_hour, hour_h, grid_h)

        # ── Draw exam blocks ──────────────────────────────────────────────
        for ex in all_exams:
            ex_date_str = ex.get('exam_date')
            for idx, dt in enumerate(week_dates):
                if dt.strftime('%Y-%m-%d') == ex_date_str:
                    self._draw_exam_block(ex, idx, day_col_w, time_col_w, header_h, start_hour, hour_h, grid_h)

        # ── Draw study sessions ───────────────────────────────────────────
        start_str = self.current_monday.strftime('%Y-%m-%d')
        end_str   = (self.current_monday + datetime.timedelta(days=6)).strftime('%Y-%m-%d')
        sessions  = queries.get_study_sessions_by_date_range(self.conn, start_str, end_str)

        for sess in sessions:
            try:
                sess_dt  = datetime.date.fromisoformat(sess['scheduled_date'])
                day_idx  = (sess_dt - self.current_monday).days
            except Exception:
                continue
            if 0 <= day_idx < 7:
                self._draw_session_card(sess, day_idx, day_col_w, time_col_w,
                                        header_h, start_hour, hour_h, grid_h)

    # ── Drawing helpers ───────────────────────────────────────────────────

    def _time_to_y(self, time_str, header_h, start_hour, hour_h):
        m   = time_to_minutes(time_str)
        rel = m - start_hour * 60
        return header_h + (rel / 60.0) * hour_h

    def _col_x(self, day_idx, day_col_w, time_col_w, margin=4):
        return time_col_w + day_idx * day_col_w + margin

    def _draw_class_block(self, s, day_idx, day_col_w, time_col_w,
                          header_h, start_hour, hour_h, grid_h):
        y1 = self._time_to_y(s['start_time'], header_h, start_hour, hour_h)
        y2 = self._time_to_y(s['end_time'],   header_h, start_hour, hour_h)
        x1 = self._col_x(day_idx, day_col_w, time_col_w)
        x2 = x1 + day_col_w - 8

        y1c = max(y1, header_h)
        y2c = min(y2, grid_h)
        if y2c <= y1c:
            return

        self.canvas.create_rectangle(x1, y1c, x2, y2c,
                                     fill='#EBE8DF', outline='#BEBBAF', dash=(3, 3))
        label = f"🏛 {s.get('subject_code','')}"
        if s.get('section'):
            label += f" • {s['section']}"
        self.canvas.create_text(x1 + 5, y1c + 7, text=label, anchor='nw',
                                font=('Segoe UI', 7, 'italic'), fill='#555555')

    def _draw_exam_block(self, ex, day_idx, day_col_w, time_col_w,
                         header_h, start_hour, hour_h, grid_h):
        y1 = self._time_to_y(ex['start_time'], header_h, start_hour, hour_h)
        y2 = self._time_to_y(ex['end_time'],   header_h, start_hour, hour_h)
        x1 = self._col_x(day_idx, day_col_w, time_col_w)
        x2 = x1 + day_col_w - 8
        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     fill='#FADBD8', outline=STATUS_MISSED, width=2)
        self.canvas.create_text(x1 + 5, y1 + 5,
                                text=f"⚠ EXAM: {ex.get('subject_code','')}",
                                anchor='nw', font=('Segoe UI', 8, 'bold'), fill='#78281F')

    def _draw_session_card(self, sess, day_idx, day_col_w, time_col_w,
                           header_h, start_hour, hour_h, grid_h):
        y1 = self._time_to_y(sess['scheduled_start'], header_h, start_hour, hour_h)
        y2 = self._time_to_y(sess['scheduled_end'],   header_h, start_hour, hour_h)
        x1 = self._col_x(day_idx, day_col_w, time_col_w, margin=6)
        x2 = x1 + day_col_w - 12

        border_c, fill_c = get_subject_colors(sess.get('subject_id', 0))
        status = sess.get('status', 'planned')
        icon   = "⏳"
        if status == 'done':
            icon = "✓"; border_c = STATUS_DONE;   fill_c = '#EAF2E8'
        elif status == 'missed':
            icon = "✕"; border_c = STATUS_MISSED; fill_c = '#FDEDEC'

        tag = f"sess_{sess['session_id']}"
        self.session_card_map[tag] = sess

        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     fill=fill_c, outline=border_c, width=2,
                                     tags=(tag, 'session_card'))
        # Time + status line
        hdr = f"{icon} {sess.get('subject_code','')}  {sess.get('scheduled_start')}–{sess.get('scheduled_end')}"
        self.canvas.create_text(x1 + 5, y1 + 4, text=hdr, anchor='nw',
                                font=('Segoe UI', 7, 'bold'), fill=border_c,
                                tags=(tag, 'session_text'))
        # Topic name
        max_chars = max(1, int((x2 - x1) / 7))
        topic = sess.get('topic_name', '')
        if len(topic) > max_chars:
            topic = topic[:max_chars - 2] + '…'
        self.canvas.create_text(x1 + 5, y1 + 17, text=topic, anchor='nw',
                                font=('Segoe UI', 7), fill=TEXT_COLOR,
                                tags=(tag, 'session_text'))

    # ═══════════════════════════════════════════════════════════════════════
    # Session interaction
    # ═══════════════════════════════════════════════════════════════════════

    def _on_canvas_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        for item in self.canvas.find_overlapping(cx - 1, cy - 1, cx + 1, cy + 1):
            for t in self.canvas.gettags(item):
                if t in self.session_card_map:
                    self._open_session_modal(self.session_card_map[t])
                    return

    def _open_session_modal(self, session):
        modal = tk.Toplevel(self)
        modal.title(f"Session #{session['session_id']}")
        modal.geometry("460x320")
        modal.configure(bg=BG_COLOR)
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        # Center it
        modal.update_idletasks()
        x = self.winfo_rootx() + self.winfo_width() // 2 - 230
        y = self.winfo_rooty() + self.winfo_height() // 2 - 160
        modal.geometry(f"+{x}+{y}")

        cnt = ttk.Frame(modal, style='TFrame', padding=20)
        cnt.pack(fill='both', expand=True)

        ttk.Label(cnt, text=f"{session.get('subject_code','')} — {session.get('subject_name','')}",
                  style='Header.TLabel').pack(anchor='w', pady=(0, 4))
        ttk.Label(cnt, text=f"Topic: {session.get('topic_name','')}",
                  font=('Segoe UI', 11, 'bold'), foreground=TEXT_COLOR).pack(anchor='w', pady=(0, 6))

        info = ttk.LabelFrame(cnt, text=" Details ", padding=10)
        info.pack(fill='x', pady=6)

        ttk.Label(info, text=(
            f"📅 {session.get('scheduled_date')}  •  "
            f"🕒 {session.get('scheduled_start')} – {session.get('scheduled_end')}"
        )).pack(anchor='w', pady=2)

        status = session.get('status', 'planned').upper()
        sc = STATUS_DONE if status == 'DONE' else (STATUS_MISSED if status == 'MISSED' else ACCENT_COLOR)
        tk.Label(info, text=f"Status: {status}", font=('Segoe UI', 10, 'bold'),
                 fg=sc, bg=BG_COLOR).pack(anchor='w', pady=2)

        btn_box = ttk.Frame(cnt, style='TFrame')
        btn_box.pack(fill='x', pady=(14, 0))

        def on_done():
            queries.update_study_session_status(self.conn, session['session_id'], 'done')
            modal.destroy()
            self.refresh()
            if self.on_data_change:
                self.on_data_change()

        def on_missed():
            res = reflow_on_missed(session['session_id'], self.conn)
            modal.destroy()
            self.refresh()
            if self.on_data_change:
                self.on_data_change()
            self.unscheduled_topics = res.get('unscheduled_topics', [])
            self._update_banner(self.unscheduled_topics)
            cnt_r = res.get('reflowed_sessions_count', 0)
            msg = f"Marked as Missed. Reflowed {cnt_r} sessions!"
            if self.unscheduled_topics:
                msg += f"\n\n⚠ {len(self.unscheduled_topics)} topic(s) have insufficient slots before exams."
            messagebox.showinfo("Adaptive Reflow", msg)

        def on_delete():
            if messagebox.askyesno("Confirm", "Delete this session?"):
                queries.delete_study_session(self.conn, session['session_id'])
                modal.destroy()
                self.refresh()
                if self.on_data_change:
                    self.on_data_change()

        ttk.Button(btn_box, text="✓ Mark Done",                 style='Accent.TButton',   command=on_done).pack(side='left', padx=3)
        ttk.Button(btn_box, text="✕ Missed (Auto-Reflow)",      style='Danger.TButton',   command=on_missed).pack(side='left', padx=3)
        ttk.Button(btn_box, text="Delete",                      style='Secondary.TButton',command=on_delete).pack(side='left', padx=3)

    # ═══════════════════════════════════════════════════════════════════════
    # Study plan generation
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_plan_dialog(self):
        if messagebox.askyesno("Auto-Generate Study Plan",
                               "Existing planned sessions will be replaced.\n"
                               "'Done' sessions are preserved.\n\nProceed?"):
            self.rebuild_study_plan()

    def rebuild_study_plan(self):
        today     = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        queries.clear_planned_study_sessions(self.conn, from_date=today_str)

        # Remaining hours = estimated – done
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT topic_id,
                   SUM((strftime('%s','2000-01-01 '||scheduled_end) -
                        strftime('%s','2000-01-01 '||scheduled_start)) / 3600.0) AS done_hrs
            FROM StudySessions WHERE status='done' GROUP BY topic_id
        """)
        done_map = {row['topic_id']: (row['done_hrs'] or 0.0) for row in cursor.fetchall()}

        topics_to_sched = []
        for t in queries.get_all_topics(self.conn):
            rem = max(0.0, round(float(t['estimated_hours']) - done_map.get(t['topic_id'], 0.0), 2))
            if rem > 0:
                tc = dict(t); tc['estimated_hours'] = rem
                topics_to_sched.append(tc)

        pivot_date = queries.get_setting(self.conn, 'pivot_date')
        pivot_do   = int(queries.get_setting(self.conn, 'pivot_day_order', '1'))

        timetable_slots = queries.get_all_timetable_slots(self.conn)
        exams           = queries.get_all_exams(self.conn)
        planning_days   = [today + datetime.timedelta(days=i) for i in range(21)]
        free_slots      = get_free_slots(timetable_slots, planning_days, exams, pivot_date, pivot_do)

        plan = build_schedule(topics_to_sched, free_slots, reference_date=today)

        with self.conn:
            for s in plan['sessions']:
                queries.insert_study_session(
                    self.conn,
                    topic_id        = s['topic_id'],
                    scheduled_date  = s['scheduled_date'],
                    scheduled_start = s['scheduled_start'],
                    scheduled_end   = s['scheduled_end'],
                    status          = 'planned',
                )

        self.unscheduled_topics = plan['unscheduled_topics']
        self._update_banner(self.unscheduled_topics)
        self.refresh()
        if self.on_data_change:
            self.on_data_change()

        msg = f"Schedule generated! {len(plan['sessions'])} sessions created."
        if self.unscheduled_topics:
            msg += f"\n\n⚠ {len(self.unscheduled_topics)} topic(s) could not be fully scheduled before exams."
        messagebox.showinfo("Planner", msg)

    # ── Banner utility ────────────────────────────────────────────────────────

    def _update_banner(self, unscheduled):
        if not unscheduled:
            self.banner_frame.pack_forget()
        else:
            names = ", ".join(
                f"{u['subject_name']}: {u['topic_name']} ({u['unallocated_hours']}h)"
                for u in unscheduled[:2]
            )
            if len(unscheduled) > 2:
                names += f" +{len(unscheduled) - 2} more"
            self.lbl_banner.config(text=f"⚠ Insufficient slots before exams: {names}")
            self.banner_frame.pack(fill='x', padx=20, pady=(0, 4), before=self.legend_frame)
