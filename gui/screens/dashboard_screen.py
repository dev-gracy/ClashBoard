"""
Dashboard Screen for ClashBoard.
Embeds matplotlib via FigureCanvasTkAgg to display:
- Planned vs Completed study hours per subject (grouped bar chart)
- Key productivity metrics (Total planned, Done, Missed, Clashes, Next Exam)
- Progress breakdown table
Styled to match the warm off-white and forest green aesthetic.
"""
import tkinter as tk
from tkinter import ttk
import datetime
from db import queries
from gui.styles import (
    BG_COLOR, CARD_BG, ACCENT_COLOR, TEXT_COLOR, MUTED_TEXT,
    BORDER_COLOR, STATUS_DONE, STATUS_MISSED, STATUS_WARNING
)

# Matplotlib imports
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class DashboardScreen(ttk.Frame):
    def __init__(self, parent, conn):
        super().__init__(parent, style='TFrame')
        self.conn = conn

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header banner
        header = ttk.Frame(self, style='TFrame')
        header.pack(fill='x', padx=20, pady=(15, 10))

        ttk.Label(
            header,
            text="Study Progress & Analytics Dashboard",
            style='Header.TLabel'
        ).pack(side='left')

        ttk.Button(
            header,
            text="🔄 Refresh Metrics",
            style='Secondary.TButton',
            command=self.refresh
        ).pack(side='right')

        # Stat cards row
        cards_frame = ttk.Frame(self, style='TFrame')
        cards_frame.pack(fill='x', padx=20, pady=(0, 15))

        self.card_planned = self._create_card(cards_frame, "Planned Study", "0.0 hrs", ACCENT_COLOR)
        self.card_planned.pack(side='left', expand=True, fill='x', padx=(0, 8))

        self.card_done = self._create_card(cards_frame, "Completed", "0.0 hrs", STATUS_DONE)
        self.card_done.pack(side='left', expand=True, fill='x', padx=(0, 8))

        self.card_missed = self._create_card(cards_frame, "Missed Sessions", "0", STATUS_MISSED)
        self.card_missed.pack(side='left', expand=True, fill='x', padx=(0, 8))

        self.card_clashes = self._create_card(cards_frame, "Active Clashes", "0", STATUS_MISSED)
        self.card_clashes.pack(side='left', expand=True, fill='x', padx=(0, 8))

        self.card_exam = self._create_card(cards_frame, "Next Exam", "None", STATUS_WARNING)
        self.card_exam.pack(side='left', expand=True, fill='x')

        # Split pane: Chart on left/top, Table on right/bottom
        split = ttk.Panedwindow(self, orient='vertical')
        split.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        # Chart Container
        chart_container = ttk.LabelFrame(split, text=" Planned vs. Completed Hours by Subject ", padding=10)
        split.add(chart_container, weight=3)

        # Matplotlib Figure
        self.fig = Figure(figsize=(8, 3.8), dpi=100, facecolor=BG_COLOR)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#FFFFFF')

        self.chart_canvas = FigureCanvasTkAgg(self.fig, master=chart_container)
        self.chart_canvas.get_tk_widget().pack(fill='both', expand=True)

        # Table Container
        table_container = ttk.LabelFrame(split, text=" Subject Study Breakdown ", padding=10)
        split.add(table_container, weight=2)

        tree_f = ttk.Frame(table_container, style='TFrame')
        tree_f.pack(fill='both', expand=True)

        cols = ('code', 'subject', 'planned', 'done', 'missed', 'rate')
        self.tree = ttk.Treeview(tree_f, columns=cols, show='headings', selectmode='browse', height=4)
        self.tree.heading('code', text='Code')
        self.tree.heading('subject', text='Subject Name')
        self.tree.heading('planned', text='Planned (hrs)')
        self.tree.heading('done', text='Done (hrs)')
        self.tree.heading('missed', text='Missed (hrs)')
        self.tree.heading('rate', text='Completion Rate')

        self.tree.column('code', width=80, anchor='center')
        self.tree.column('subject', width=240, anchor='w')
        self.tree.column('planned', width=100, anchor='center')
        self.tree.column('done', width=100, anchor='center')
        self.tree.column('missed', width=100, anchor='center')
        self.tree.column('rate', width=120, anchor='center')

        scroll = ttk.Scrollbar(tree_f, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

    def _create_card(self, parent, title, initial_val, color):
        card = ttk.Frame(parent, style='Card.TFrame', padding=(14, 10))
        lbl_title = ttk.Label(card, text=title, style='CardMuted.TLabel')
        lbl_title.pack(anchor='w')
        lbl_val = tk.Label(
            card,
            text=initial_val,
            font=('Segoe UI', 16, 'bold'),
            fg=color,
            bg=CARD_BG
        )
        lbl_val.pack(anchor='w')
        card.val_widget = lbl_val
        return card

    def refresh(self):
        """Fetches data and redraws chart & metrics."""
        summary_rows = queries.get_all_sessions_summary_by_subject(self.conn)
        clashes = queries.get_all_clashes(self.conn)
        exams = queries.get_all_exams(self.conn)

        # 1. Update Metric Cards
        tot_planned = sum(r['planned_hours'] for r in summary_rows)
        tot_done = sum(r['done_hours'] for r in summary_rows)
        tot_missed = sum(r['missed_hours'] for r in summary_rows)

        self.card_planned.val_widget.config(text=f"{tot_planned:.1f} hrs")
        self.card_done.val_widget.config(text=f"{tot_done:.1f} hrs")

        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM StudySessions WHERE status = 'missed'")
        missed_count = cursor.fetchone()[0]
        self.card_missed.val_widget.config(text=str(missed_count))

        self.card_clashes.val_widget.config(text=str(len(clashes)))

        # Next Exam Countdown
        today = datetime.date.today()
        upcoming_exams = []
        for e in exams:
            try:
                ex_dt = datetime.date.fromisoformat(e['exam_date'])
                days = (ex_dt - today).days
                if days >= 0:
                    upcoming_exams.append((days, e))
            except Exception:
                pass

        if upcoming_exams:
            upcoming_exams.sort(key=lambda x: x[0])
            next_days, next_ex = upcoming_exams[0]
            day_str = f"In {next_days} days" if next_days > 0 else "TODAY!"
            self.card_exam.val_widget.config(text=f"{next_ex['subject_code']} ({day_str})")
        else:
            self.card_exam.val_widget.config(text="None scheduled")

        # 2. Update Table
        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in summary_rows:
            p_hrs = r['planned_hours']
            d_hrs = r['done_hours']
            m_hrs = r['missed_hours']
            tot_req = p_hrs + d_hrs + m_hrs
            pct_str = f"{(d_hrs / tot_req * 100):.1f}%" if tot_req > 0 else "0.0%"

            self.tree.insert(
                '',
                'end',
                values=(
                    r['subject_code'] or '',
                    r['subject_name'],
                    f"{p_hrs:.1f}",
                    f"{d_hrs:.1f}",
                    f"{m_hrs:.1f}",
                    pct_str
                )
            )

        # 3. Redraw Matplotlib Bar Chart
        self.ax.clear()
        self.ax.set_facecolor('#FFFFFF')

        labels = [r['subject_code'] or r['subject_name'][:10] for r in summary_rows]
        planned_vals = [r['planned_hours'] for r in summary_rows]
        done_vals = [r['done_hours'] for r in summary_rows]

        if labels:
            import numpy as np
            x = np.arange(len(labels))
            width = 0.35

            self.ax.bar(x - width/2, planned_vals, width, label='Planned (hrs)', color='#5B84B1', edgecolor='#436488', alpha=0.9)
            self.ax.bar(x + width/2, done_vals, width, label='Completed (hrs)', color='#2F5233', edgecolor='#1F3622', alpha=0.95)

            self.ax.set_ylabel('Hours', fontsize=9, color=TEXT_COLOR, fontname='Segoe UI')
            self.ax.set_xticks(x)
            self.ax.set_xticklabels(labels, fontsize=9, color=TEXT_COLOR, fontname='Segoe UI')
            self.ax.grid(axis='y', linestyle='--', alpha=0.3, color='#AAAAAA')
            self.ax.legend(loc='upper right', frameon=True, facecolor=BG_COLOR, edgecolor=BORDER_COLOR, fontsize=8)

            # Spines styling
            for spine in self.ax.spines.values():
                spine.set_color(BORDER_COLOR)

        self.fig.tight_layout()
        self.chart_canvas.draw()

