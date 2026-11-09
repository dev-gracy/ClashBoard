"""
Timetable Screen for ClashBoard.
Allows adding, editing, and deleting timetable slots and exam schedules.
Displays entries in a structured, styled Treeview with filters and conflict checks.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from db import queries
from services.clash_detector import detect_clashes
from gui.styles import BG_COLOR, CARD_BG, ACCENT_COLOR, TEXT_COLOR, MUTED_TEXT


class TimetableScreen(ttk.Frame):
    def __init__(self, parent, conn, on_clash_detected=None):
        super().__init__(parent, style='TFrame')
        self.conn = conn
        self.on_clash_detected = on_clash_detected

        self.selected_slot_id = None
        self.selected_exam_id = None

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Header banner
        header_frame = ttk.Frame(self, style='TFrame')
        header_frame.pack(fill='x', padx=20, pady=(15, 10))

        ttk.Label(
            header_frame,
            text="Weekly Timetable & Exams",
            style='Header.TLabel'
        ).pack(side='left')

        ttk.Button(
            header_frame,
            text="⚡ Scan for Clashes",
            style='Accent.TButton',
            command=self._scan_clashes
        ).pack(side='right')

        # Main splitter (Top: Timetable, Bottom: Exams)
        paned = ttk.Panedwindow(self, orient='vertical')
        paned.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        # --- TIMETABLE SECTION ---
        tt_container = ttk.LabelFrame(paned, text=" Recurring Weekly Classes ", padding=10)
        paned.add(tt_container, weight=3)

        # Timetable split: Left list, Right form
        tt_split = ttk.Frame(tt_container, style='TFrame')
        tt_split.pack(fill='both', expand=True)

        # Left: Treeview
        tree_frame = ttk.Frame(tt_split, style='TFrame')
        tree_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        columns = ('slot_id', 'day', 'time', 'code', 'subject', 'section')
        self.tt_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        self.tt_tree.heading('slot_id', text='ID')
        self.tt_tree.heading('day', text='Day')
        self.tt_tree.heading('time', text='Time Window')
        self.tt_tree.heading('code', text='Code')
        self.tt_tree.heading('subject', text='Subject')
        self.tt_tree.heading('section', text='Section / Type')

        self.tt_tree.column('slot_id', width=45, anchor='center')
        self.tt_tree.column('day', width=60, anchor='center')
        self.tt_tree.column('time', width=120, anchor='center')
        self.tt_tree.column('code', width=80, anchor='center')
        self.tt_tree.column('subject', width=220, anchor='w')
        self.tt_tree.column('section', width=120, anchor='w')

        tt_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tt_tree.yview)
        self.tt_tree.configure(yscrollcommand=tt_scroll.set)
        self.tt_tree.pack(side='left', fill='both', expand=True)
        tt_scroll.pack(side='right', fill='y')

        self.tt_tree.bind('<<TreeviewSelect>>', self._on_tt_select)

        # Right: Timetable Form
        tt_form = ttk.LabelFrame(tt_split, text=" Add / Edit Class ", padding=12)
        tt_form.pack(side='right', fill='y', padx=(5, 0))

        ttk.Label(tt_form, text="Subject:").grid(row=0, column=0, sticky='w', pady=4)
        self.cb_subject = ttk.Combobox(tt_form, state='readonly', width=22)
        self.cb_subject.grid(row=0, column=1, pady=4, padx=4)

        ttk.Label(tt_form, text="Day of Week:").grid(row=1, column=0, sticky='w', pady=4)
        self.cb_day = ttk.Combobox(tt_form, values=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], state='readonly', width=22)
        self.cb_day.set('Mon')
        self.cb_day.grid(row=1, column=1, pady=4, padx=4)

        ttk.Label(tt_form, text="Start Time (HH:MM):").grid(row=2, column=0, sticky='w', pady=4)
        self.entry_start = ttk.Entry(tt_form, width=24)
        self.entry_start.insert(0, "10:00")
        self.entry_start.grid(row=2, column=1, pady=4, padx=4)

        ttk.Label(tt_form, text="End Time (HH:MM):").grid(row=3, column=0, sticky='w', pady=4)
        self.entry_end = ttk.Entry(tt_form, width=24)
        self.entry_end.insert(0, "11:30")
        self.entry_end.grid(row=3, column=1, pady=4, padx=4)

        ttk.Label(tt_form, text="Section / Room:").grid(row=4, column=0, sticky='w', pady=4)
        self.entry_sec = ttk.Entry(tt_form, width=24)
        self.entry_sec.insert(0, "Lecture Hall 1")
        self.entry_sec.grid(row=4, column=1, pady=4, padx=4)

        btn_box = ttk.Frame(tt_form, style='TFrame')
        btn_box.grid(row=5, column=0, columnspan=2, pady=(15, 0))

        self.btn_save_slot = ttk.Button(btn_box, text="Save Class", style='Accent.TButton', command=self._save_slot)
        self.btn_save_slot.pack(side='left', padx=3)

        self.btn_del_slot = ttk.Button(btn_box, text="Delete", style='Danger.TButton', command=self._delete_slot)
        self.btn_del_slot.pack(side='left', padx=3)

        self.btn_clear_slot = ttk.Button(btn_box, text="Clear", style='Secondary.TButton', command=self._clear_tt_form)
        self.btn_clear_slot.pack(side='left', padx=3)

        # --- EXAMS SECTION ---
        ex_container = ttk.LabelFrame(paned, text=" Upcoming Scheduled Exams ", padding=10)
        paned.add(ex_container, weight=2)

        ex_split = ttk.Frame(ex_container, style='TFrame')
        ex_split.pack(fill='both', expand=True)

        # Exam list
        ex_tree_frame = ttk.Frame(ex_split, style='TFrame')
        ex_tree_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))

        ex_cols = ('exam_id', 'date', 'time', 'code', 'subject')
        self.ex_tree = ttk.Treeview(ex_tree_frame, columns=ex_cols, show='headings', selectmode='browse')
        self.ex_tree.heading('exam_id', text='ID')
        self.ex_tree.heading('date', text='Exam Date')
        self.ex_tree.heading('time', text='Time Window')
        self.ex_tree.heading('code', text='Code')
        self.ex_tree.heading('subject', text='Subject')

        self.ex_tree.column('exam_id', width=45, anchor='center')
        self.ex_tree.column('date', width=110, anchor='center')
        self.ex_tree.column('time', width=120, anchor='center')
        self.ex_tree.column('code', width=80, anchor='center')
        self.ex_tree.column('subject', width=240, anchor='w')

        ex_scroll = ttk.Scrollbar(ex_tree_frame, orient='vertical', command=self.ex_tree.yview)
        self.ex_tree.configure(yscrollcommand=ex_scroll.set)
        self.ex_tree.pack(side='left', fill='both', expand=True)
        ex_scroll.pack(side='right', fill='y')

        self.ex_tree.bind('<<TreeviewSelect>>', self._on_ex_select)

        # Exam Form
        ex_form = ttk.LabelFrame(ex_split, text=" Add / Edit Exam ", padding=12)
        ex_form.pack(side='right', fill='y', padx=(5, 0))

        ttk.Label(ex_form, text="Subject:").grid(row=0, column=0, sticky='w', pady=4)
        self.cb_exam_subject = ttk.Combobox(ex_form, state='readonly', width=22)
        self.cb_exam_subject.grid(row=0, column=1, pady=4, padx=4)

        ttk.Label(ex_form, text="Date (YYYY-MM-DD):").grid(row=1, column=0, sticky='w', pady=4)
        self.entry_exam_date = ttk.Entry(ex_form, width=24)
        self.entry_exam_date.grid(row=1, column=1, pady=4, padx=4)

        ttk.Label(ex_form, text="Start Time (HH:MM):").grid(row=2, column=0, sticky='w', pady=4)
        self.entry_exam_start = ttk.Entry(ex_form, width=24)
        self.entry_exam_start.insert(0, "09:00")
        self.entry_exam_start.grid(row=2, column=1, pady=4, padx=4)

        ttk.Label(ex_form, text="End Time (HH:MM):").grid(row=3, column=0, sticky='w', pady=4)
        self.entry_exam_end = ttk.Entry(ex_form, width=24)
        self.entry_exam_end.insert(0, "11:00")
        self.entry_exam_end.grid(row=3, column=1, pady=4, padx=4)

        ex_btn_box = ttk.Frame(ex_form, style='TFrame')
        ex_btn_box.grid(row=4, column=0, columnspan=2, pady=(15, 0))

        self.btn_save_exam = ttk.Button(ex_btn_box, text="Save Exam", style='Accent.TButton', command=self._save_exam)
        self.btn_save_exam.pack(side='left', padx=3)

        self.btn_del_exam = ttk.Button(ex_btn_box, text="Delete", style='Danger.TButton', command=self._delete_exam)
        self.btn_del_exam.pack(side='left', padx=3)

        self.btn_clear_exam = ttk.Button(ex_btn_box, text="Clear", style='Secondary.TButton', command=self._clear_exam_form)
        self.btn_clear_exam.pack(side='left', padx=3)

    def refresh(self):
        """Reloads subjects, timetable slots, and exams."""
        # Load subjects for dropdowns
        subjects = queries.get_all_subjects(self.conn)
        self.subject_map = {f"{s['code']} - {s['name']}": s['subject_id'] for s in subjects}
        sub_names = list(self.subject_map.keys())

        self.cb_subject['values'] = sub_names
        self.cb_exam_subject['values'] = sub_names
        if sub_names:
            if not self.cb_subject.get() or self.cb_subject.get() not in sub_names:
                self.cb_subject.set(sub_names[0])
            if not self.cb_exam_subject.get() or self.cb_exam_subject.get() not in sub_names:
                self.cb_exam_subject.set(sub_names[0])

        # Load timetable
        for item in self.tt_tree.get_children():
            self.tt_tree.delete(item)

        slots = queries.get_all_timetable_slots(self.conn)
        for s in slots:
            self.tt_tree.insert(
                '',
                'end',
                iid=str(s['slot_id']),
                values=(
                    s['slot_id'],
                    s['day_of_week'],
                    f"{s['start_time']} - {s['end_time']}",
                    s['subject_code'] or '',
                    s['subject_name'],
                    s['section'] or ''
                )
            )

        # Load exams
        for item in self.ex_tree.get_children():
            self.ex_tree.delete(item)

        exams = queries.get_all_exams(self.conn)
        for e in exams:
            self.ex_tree.insert(
                '',
                'end',
                iid=str(e['exam_id']),
                values=(
                    e['exam_id'],
                    e['exam_date'],
                    f"{e['start_time']} - {e['end_time']}",
                    e['subject_code'] or '',
                    e['subject_name']
                )
            )

    def _on_tt_select(self, event):
        sel = self.tt_tree.selection()
        if not sel:
            return
        slot_id = int(sel[0])
        slot = queries.get_timetable_slot_by_id(self.conn, slot_id)
        if not slot:
            return
        self.selected_slot_id = slot_id
        for name, sid in self.subject_map.items():
            if sid == slot['subject_id']:
                self.cb_subject.set(name)
                break
        self.cb_day.set(slot['day_of_week'])
        self.entry_start.delete(0, 'end')
        self.entry_start.insert(0, slot['start_time'])
        self.entry_end.delete(0, 'end')
        self.entry_end.insert(0, slot['end_time'])
        self.entry_sec.delete(0, 'end')
        self.entry_sec.insert(0, slot['section'] or '')

    def _clear_tt_form(self):
        self.selected_slot_id = None
        self.tt_tree.selection_remove(self.tt_tree.selection())
        self.entry_start.delete(0, 'end')
        self.entry_start.insert(0, "10:00")
        self.entry_end.delete(0, 'end')
        self.entry_end.insert(0, "11:30")
        self.entry_sec.delete(0, 'end')
        self.entry_sec.insert(0, "Lecture")

    def _save_slot(self):
        sub_name = self.cb_subject.get()
        if sub_name not in self.subject_map:
            messagebox.showwarning("Validation Error", "Please select a valid subject.")
            return

        subject_id = self.subject_map[sub_name]
        day = self.cb_day.get()
        start = self.entry_start.get().strip()
        end = self.entry_end.get().strip()
        sec = self.entry_sec.get().strip()

        if not start or not end:
            messagebox.showwarning("Validation Error", "Start and End times are required.")
            return

        if self.selected_slot_id:
            queries.update_timetable_slot(self.conn, self.selected_slot_id, subject_id, day, start, end, sec)
        else:
            queries.insert_timetable_slot(self.conn, subject_id, day, start, end, sec)

        self._clear_tt_form()
        self.refresh()
        self._auto_rescan()

    def _delete_slot(self):
        if not self.selected_slot_id:
            messagebox.showinfo("Select Class", "Please select a class from the list to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this timetable slot?"):
            queries.delete_timetable_slot(self.conn, self.selected_slot_id)
            self._clear_tt_form()
            self.refresh()
            self._auto_rescan()

    def _on_ex_select(self, event):
        sel = self.ex_tree.selection()
        if not sel:
            return
        exam_id = int(sel[0])
        exam = queries.get_exam_by_id(self.conn, exam_id)
        if not exam:
            return
        self.selected_exam_id = exam_id
        for name, sid in self.subject_map.items():
            if sid == exam['subject_id']:
                self.cb_exam_subject.set(name)
                break
        self.entry_exam_date.delete(0, 'end')
        self.entry_exam_date.insert(0, exam['exam_date'])
        self.entry_exam_start.delete(0, 'end')
        self.entry_exam_start.insert(0, exam['start_time'])
        self.entry_exam_end.delete(0, 'end')
        self.entry_exam_end.insert(0, exam['end_time'])

    def _clear_exam_form(self):
        self.selected_exam_id = None
        self.ex_tree.selection_remove(self.ex_tree.selection())
        self.entry_exam_date.delete(0, 'end')
        self.entry_exam_start.delete(0, 'end')
        self.entry_exam_start.insert(0, "09:00")
        self.entry_exam_end.delete(0, 'end')
        self.entry_exam_end.insert(0, "11:00")

    def _save_exam(self):
        sub_name = self.cb_exam_subject.get()
        if sub_name not in self.subject_map:
            messagebox.showwarning("Validation Error", "Please select a valid subject.")
            return

        subject_id = self.subject_map[sub_name]
        edate = self.entry_exam_date.get().strip()
        start = self.entry_exam_start.get().strip()
        end = self.entry_exam_end.get().strip()

        if not edate or not start or not end:
            messagebox.showwarning("Validation Error", "Exam date, start, and end times are required.")
            return

        if self.selected_exam_id:
            queries.update_exam(self.conn, self.selected_exam_id, subject_id, edate, start, end)
        else:
            queries.insert_exam(self.conn, subject_id, edate, start, end)

        self._clear_exam_form()
        self.refresh()
        self._auto_rescan()

    def _delete_exam(self):
        if not self.selected_exam_id:
            messagebox.showinfo("Select Exam", "Please select an exam from the list to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this scheduled exam?"):
            queries.delete_exam(self.conn, self.selected_exam_id)
            self._clear_exam_form()
            self.refresh()
            self._auto_rescan()

    def _auto_rescan(self):
        slots = queries.get_all_timetable_slots(self.conn)
        exams = queries.get_all_exams(self.conn)
        clashes = detect_clashes(slots, exams)
        queries.save_clashes(self.conn, clashes)
        if self.on_clash_detected:
            self.on_clash_detected(len(clashes))

    def _scan_clashes(self):
        slots = queries.get_all_timetable_slots(self.conn)
        exams = queries.get_all_exams(self.conn)
        clashes = detect_clashes(slots, exams)
        queries.save_clashes(self.conn, clashes)
        if self.on_clash_detected:
            self.on_clash_detected(len(clashes))

        if clashes:
            messagebox.showwarning(
                "Conflicts Detected!",
                f"Found {len(clashes)} timetable/exam clash(es)!\n"
                "Switch to the 'Clash Report' screen from the sidebar to view details and resolution guidance."
            )
        else:
            messagebox.showinfo(
                "No Clashes",
                "Great news! Zero conflicts found between your timetable classes and scheduled exams."
            )

