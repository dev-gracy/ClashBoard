"""
Clash Report Screen for ClashBoard.
Displays detected conflicts in plain English, grouped by type:
- class-class
- class-exam
- exam-exam
Includes summary counters, filtering, and actionable resolution guidance.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from db import queries
from services.clash_detector import detect_clashes
from gui.styles import (
    BG_COLOR, CARD_BG, ACCENT_COLOR, TEXT_COLOR, MUTED_TEXT,
    STATUS_MISSED, STATUS_WARNING, STATUS_DONE
)


class ClashScreen(ttk.Frame):
    def __init__(self, parent, conn, on_clash_update=None):
        super().__init__(parent, style='TFrame')
        self.conn = conn
        self.on_clash_update = on_clash_update

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header banner
        header = ttk.Frame(self, style='TFrame')
        header.pack(fill='x', padx=20, pady=(15, 10))

        ttk.Label(
            header,
            text="Schedule Conflict & Clash Report",
            style='Header.TLabel'
        ).pack(side='left')

        ttk.Button(
            header,
            text="🔄 Re-scan All Clashes",
            style='Accent.TButton',
            command=self.rescan
        ).pack(side='right')

        # Stat Cards Frame
        cards_frame = ttk.Frame(self, style='TFrame')
        cards_frame.pack(fill='x', padx=20, pady=(0, 15))

        self.card_total = self._create_stat_card(cards_frame, "Total Conflicts", "0", STATUS_MISSED)
        self.card_total.pack(side='left', expand=True, fill='x', padx=(0, 8))

        self.card_class_class = self._create_stat_card(cards_frame, "Class ↔ Class", "0", STATUS_WARNING)
        self.card_class_class.pack(side='left', expand=True, fill='x', padx=(0, 8))

        self.card_class_exam = self._create_stat_card(cards_frame, "Class ↔ Exam", "0", STATUS_WARNING)
        self.card_class_exam.pack(side='left', expand=True, fill='x', padx=(0, 8))

        self.card_exam_exam = self._create_stat_card(cards_frame, "Exam ↔ Exam", "0", STATUS_MISSED)
        self.card_exam_exam.pack(side='left', expand=True, fill='x')

        # Main Splitter
        paned = ttk.Panedwindow(self, orient='vertical')
        paned.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        # Conflict Table Section
        table_container = ttk.LabelFrame(paned, text=" Detected Conflicts ", padding=10)
        paned.add(table_container, weight=3)

        # Filter bar
        filter_bar = ttk.Frame(table_container, style='TFrame')
        filter_bar.pack(fill='x', pady=(0, 8))

        ttk.Label(filter_bar, text="Filter by Type:").pack(side='left', padx=(0, 6))
        self.filter_var = tk.StringVar(value="All")
        cb_filter = ttk.Combobox(
            filter_bar,
            textvariable=self.filter_var,
            values=["All", "Class vs Class", "Class vs Exam", "Exam vs Exam"],
            state='readonly',
            width=18
        )
        cb_filter.pack(side='left')
        cb_filter.bind('<<ComboboxSelected>>', lambda e: self._apply_filter())

        self.lbl_status = ttk.Label(filter_bar, text="", style='Muted.TLabel')
        self.lbl_status.pack(side='right')

        # Conflict Treeview
        tree_frame = ttk.Frame(table_container, style='TFrame')
        tree_frame.pack(fill='both', expand=True)

        cols = ('id', 'type', 'description', 'detected_on')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        self.tree.heading('id', text='#')
        self.tree.heading('type', text='Conflict Type')
        self.tree.heading('description', text='Plain-English Details')
        self.tree.heading('detected_on', text='Detected At')

        self.tree.column('id', width=45, anchor='center')
        self.tree.column('type', width=130, anchor='center')
        self.tree.column('description', width=600, anchor='w')
        self.tree.column('detected_on', width=150, anchor='center')

        scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        self.tree.bind('<<TreeviewSelect>>', self._on_select_clash)

        # Resolution Guidance Section
        self.guide_container = ttk.LabelFrame(paned, text=" Actionable Resolution Advice ", padding=12)
        paned.add(self.guide_container, weight=1)

        self.lbl_guide_title = ttk.Label(self.guide_container, text="Select a conflict above to view recommended action.", style='SubHeader.TLabel')
        self.lbl_guide_title.pack(anchor='w', pady=(0, 4))

        self.lbl_guide_desc = ttk.Label(
            self.guide_container,
            text="ClashBoard automatically checks your timetable whenever you update classes or upcoming exams.",
            wraplength=850,
            style='Muted.TLabel'
        )
        self.lbl_guide_desc.pack(anchor='w')

    def _create_stat_card(self, parent, title, initial_val, color):
        card = ttk.Frame(parent, style='Card.TFrame', padding=(14, 10))
        lbl_title = ttk.Label(card, text=title, style='CardMuted.TLabel')
        lbl_title.pack(anchor='w')
        lbl_val = tk.Label(
            card,
            text=initial_val,
            font=('Segoe UI', 18, 'bold'),
            fg=color,
            bg=CARD_BG
        )
        lbl_val.pack(anchor='w')
        card.val_widget = lbl_val
        return card

    def refresh(self):
        """Loads clashes from DB into table and updates metrics."""
        self.all_clashes = queries.get_all_clashes(self.conn)
        self._apply_filter()
        self._update_metrics()

    def _apply_filter(self):
        filter_val = self.filter_var.get()
        for item in self.tree.get_children():
            self.tree.delete(item)

        for c in self.all_clashes:
            ctype = c.get('clash_type', '')
            # Filter matching
            if filter_val == "Class vs Class" and ctype != 'class-class':
                continue
            if filter_val == "Class vs Exam" and ctype != 'class-exam':
                continue
            if filter_val == "Exam vs Exam" and ctype != 'exam-exam':
                continue

            # Format readable badge
            type_label = {
                'class-class': "Class ↔ Class",
                'class-exam': "Class ↔ Exam",
                'exam-exam': "Exam ↔ Exam"
            }.get(ctype, ctype)

            self.tree.insert(
                '',
                'end',
                iid=str(c['clash_id']),
                values=(
                    c['clash_id'],
                    type_label,
                    c.get('description', ''),
                    c.get('detected_on', '')
                )
            )

        total_cnt = len(self.all_clashes)
        if total_cnt == 0:
            self.lbl_status.config(text="✓ No clashes detected.", foreground=STATUS_DONE)
        else:
            self.lbl_status.config(text=f"⚠️ {total_cnt} conflict(s) requiring attention.", foreground=STATUS_MISSED)

    def _update_metrics(self):
        total = len(self.all_clashes)
        cc = sum(1 for c in self.all_clashes if c.get('clash_type') == 'class-class')
        ce = sum(1 for c in self.all_clashes if c.get('clash_type') == 'class-exam')
        ee = sum(1 for c in self.all_clashes if c.get('clash_type') == 'exam-exam')

        self.card_total.val_widget.config(text=str(total))
        self.card_class_class.val_widget.config(text=str(cc))
        self.card_class_exam.val_widget.config(text=str(ce))
        self.card_exam_exam.val_widget.config(text=str(ee))

    def _on_select_clash(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        clash_id = int(sel[0])
        clash = next((c for c in self.all_clashes if c['clash_id'] == clash_id), None)
        if not clash:
            return

        ctype = clash.get('clash_type', '')
        desc = clash.get('description', '')

        if ctype == 'class-class':
            self.lbl_guide_title.config(
                text="🚨 Class Overlap Recommendation",
                foreground=STATUS_MISSED
            )
            self.lbl_guide_desc.config(
                text=(
                    f"Conflict: {desc}\n\n"
                    "Recommended Action:\n"
                    "• Check if alternate lecture or lab sections exist for either course in your student portal.\n"
                    "• If one course is an elective, consider switching to another section or elective slot.\n"
                    "• Speak with your academic advisor or course instructors if attendance is mandatory in both."
                )
            )
        elif ctype == 'class-exam':
            self.lbl_guide_title.config(
                text="⚠️ Class vs Exam Conflict Recommendation",
                foreground=STATUS_WARNING
            )
            self.lbl_guide_desc.config(
                text=(
                    f"Conflict: {desc}\n\n"
                    "Recommended Action:\n"
                    "• Exams take precedence over regular classes.\n"
                    "• Notify your class instructor in advance that you have a scheduled exam at this time.\n"
                    "• Request lecture notes or recording access for the class session you will miss."
                )
            )
        elif ctype == 'exam-exam':
            self.lbl_guide_title.config(
                text="⚡ Critical Exam Clash Recommendation",
                foreground=STATUS_MISSED
            )
            self.lbl_guide_desc.config(
                text=(
                    f"Conflict: {desc}\n\n"
                    "Recommended Action:\n"
                    "• CRITICAL: You cannot be in two exams at the same time!\n"
                    "• Submit an immediate formal exam clash form to the university registrar/examination office.\n"
                    "• Most universities provide a makeup session or rescheduled sitting for documented exam overlaps."
                )
            )

    def rescan(self):
        """Forces a full re-detection of clashes against current DB timetable & exams."""
        slots = queries.get_all_timetable_slots(self.conn)
        exams = queries.get_all_exams(self.conn)
        pivot_date = queries.get_setting(self.conn, 'pivot_date')
        pivot_do = int(queries.get_setting(self.conn, 'pivot_day_order', '1'))
        clashes = detect_clashes(slots, exams, pivot_date, pivot_do)
        queries.save_clashes(self.conn, clashes)
        self.refresh()
        if self.on_clash_update:
            self.on_clash_update(len(clashes))
        messagebox.showinfo("Scan Complete", f"Scan finished. Found {len(clashes)} conflict(s).")

