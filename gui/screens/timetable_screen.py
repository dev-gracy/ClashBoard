"""
Timetable Screen for ClashBoard.
Manages recurring class slots (Day Order 1–5) and upcoming exams.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from db import queries
from services.clash_detector import detect_clashes
from gui.styles import BG_COLOR, ACCENT_COLOR, TEXT_COLOR, MUTED_TEXT

DAY_ORDER_OPTIONS = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5"]
DO_LABEL_TO_INT   = {f"Day {i}": i for i in range(1, 6)}
DO_INT_TO_LABEL   = {i: f"Day {i}" for i in range(1, 6)}


class TimetableScreen(ttk.Frame):
    def __init__(self, parent, conn, on_clash_detected=None):
        super().__init__(parent, style='TFrame')
        self.conn              = conn
        self.on_clash_detected = on_clash_detected
        self.selected_slot_id  = None
        self.selected_exam_id  = None
        self._build_ui()
        self.refresh()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        hdr = ttk.Frame(self, style='TFrame')
        hdr.pack(fill='x', padx=20, pady=(15, 10))
        ttk.Label(hdr, text="Timetable (Day Order) & Exams", style='Header.TLabel').pack(side='left')
        ttk.Button(hdr, text="⚡ Scan for Clashes", style='Accent.TButton',
                   command=self._scan_clashes).pack(side='right')

        paned = ttk.Panedwindow(self, orient='vertical')
        paned.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        # ── Timetable pane ────────────────────────────────────────────────
        tt_pane = ttk.LabelFrame(paned, text=" Recurring Classes (by Day Order) ", padding=10)
        paned.add(tt_pane, weight=3)

        tt_split = ttk.Frame(tt_pane, style='TFrame')
        tt_split.pack(fill='both', expand=True)

        # Timetable Treeview
        tf = ttk.Frame(tt_split, style='TFrame')
        tf.pack(side='left', fill='both', expand=True, padx=(0, 10))

        cols = ('id', 'do', 'time', 'code', 'subject', 'room')
        self.tt_tree = ttk.Treeview(tf, columns=cols, show='headings', selectmode='browse')
        for col, hd, w in [('id','ID',45),('do','Day Order',80),('time','Period',130),
                            ('code','Code',65),('subject','Subject',230),('room','Room / Mode',120)]:
            self.tt_tree.heading(col, text=hd)
            self.tt_tree.column(col, width=w, anchor='center' if col != 'subject' else 'w')

        tt_sc = ttk.Scrollbar(tf, orient='vertical', command=self.tt_tree.yview)
        self.tt_tree.configure(yscrollcommand=tt_sc.set)
        self.tt_tree.pack(side='left', fill='both', expand=True)
        tt_sc.pack(side='right', fill='y')
        self.tt_tree.bind('<<TreeviewSelect>>', self._on_tt_select)

        # Timetable form
        tt_form = ttk.LabelFrame(tt_split, text=" Add / Edit Class ", padding=12)
        tt_form.pack(side='right', fill='y', padx=(5, 0))

        self._form_row(tt_form, 0, "Subject:")
        self.cb_subject = ttk.Combobox(tt_form, state='readonly', width=22)
        self.cb_subject.grid(row=0, column=1, pady=4, padx=4)

        self._form_row(tt_form, 1, "Day Order:")
        self.cb_day_order = ttk.Combobox(tt_form, values=DAY_ORDER_OPTIONS, state='readonly', width=22)
        self.cb_day_order.set("Day 1")
        self.cb_day_order.grid(row=1, column=1, pady=4, padx=4)

        self._form_row(tt_form, 2, "Start (HH:MM):")
        self.entry_start = ttk.Entry(tt_form, width=24)
        self.entry_start.insert(0, "09:45")
        self.entry_start.grid(row=2, column=1, pady=4, padx=4)

        self._form_row(tt_form, 3, "End (HH:MM):")
        self.entry_end = ttk.Entry(tt_form, width=24)
        self.entry_end.insert(0, "10:35")
        self.entry_end.grid(row=3, column=1, pady=4, padx=4)

        self._form_row(tt_form, 4, "Room / Mode:")
        self.entry_sec = ttk.Entry(tt_form, width=24)
        self.entry_sec.insert(0, "TP 704")
        self.entry_sec.grid(row=4, column=1, pady=4, padx=4)

        btn_box = ttk.Frame(tt_form, style='TFrame')
        btn_box.grid(row=5, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(btn_box, text="Save Class", style='Accent.TButton',   command=self._save_slot).pack(side='left', padx=3)
        ttk.Button(btn_box, text="Delete",     style='Danger.TButton',   command=self._delete_slot).pack(side='left', padx=3)
        ttk.Button(btn_box, text="Clear",      style='Secondary.TButton',command=self._clear_tt_form).pack(side='left', padx=3)

        # ── Exam pane ─────────────────────────────────────────────────────
        ex_pane = ttk.LabelFrame(paned, text=" Scheduled Exams ", padding=10)
        paned.add(ex_pane, weight=2)

        ex_split = ttk.Frame(ex_pane, style='TFrame')
        ex_split.pack(fill='both', expand=True)

        ef = ttk.Frame(ex_split, style='TFrame')
        ef.pack(side='left', fill='both', expand=True, padx=(0, 10))

        ex_cols = ('id', 'date', 'time', 'code', 'subject')
        self.ex_tree = ttk.Treeview(ef, columns=ex_cols, show='headings', selectmode='browse')
        for col, hd, w in [('id','ID',45),('date','Exam Date',110),('time','Period',130),
                            ('code','Code',65),('subject','Subject',250)]:
            self.ex_tree.heading(col, text=hd)
            self.ex_tree.column(col, width=w, anchor='center' if col != 'subject' else 'w')

        ex_sc = ttk.Scrollbar(ef, orient='vertical', command=self.ex_tree.yview)
        self.ex_tree.configure(yscrollcommand=ex_sc.set)
        self.ex_tree.pack(side='left', fill='both', expand=True)
        ex_sc.pack(side='right', fill='y')
        self.ex_tree.bind('<<TreeviewSelect>>', self._on_ex_select)

        ex_form = ttk.LabelFrame(ex_split, text=" Add / Edit Exam ", padding=12)
        ex_form.pack(side='right', fill='y', padx=(5, 0))

        self._form_row(ex_form, 0, "Subject:")
        self.cb_exam_sub = ttk.Combobox(ex_form, state='readonly', width=22)
        self.cb_exam_sub.grid(row=0, column=1, pady=4, padx=4)

        self._form_row(ex_form, 1, "Date (YYYY-MM-DD):")
        self.entry_exam_date = ttk.Entry(ex_form, width=24)
        self.entry_exam_date.grid(row=1, column=1, pady=4, padx=4)

        self._form_row(ex_form, 2, "Start (HH:MM):")
        self.entry_exam_start = ttk.Entry(ex_form, width=24)
        self.entry_exam_start.insert(0, "09:00")
        self.entry_exam_start.grid(row=2, column=1, pady=4, padx=4)

        self._form_row(ex_form, 3, "End (HH:MM):")
        self.entry_exam_end = ttk.Entry(ex_form, width=24)
        self.entry_exam_end.insert(0, "12:00")
        self.entry_exam_end.grid(row=3, column=1, pady=4, padx=4)

        ex_btn_box = ttk.Frame(ex_form, style='TFrame')
        ex_btn_box.grid(row=4, column=0, columnspan=2, pady=(15, 0))
        ttk.Button(ex_btn_box, text="Save Exam", style='Accent.TButton',   command=self._save_exam).pack(side='left', padx=3)
        ttk.Button(ex_btn_box, text="Delete",    style='Danger.TButton',   command=self._delete_exam).pack(side='left', padx=3)
        ttk.Button(ex_btn_box, text="Clear",     style='Secondary.TButton',command=self._clear_exam_form).pack(side='left', padx=3)

    def _form_row(self, parent, row, label):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=4)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def refresh(self):
        subjects = queries.get_all_subjects(self.conn)
        self.subject_map = {f"{s['code']} – {s['name']}": s['subject_id'] for s in subjects}
        sub_list = list(self.subject_map.keys())

        self.cb_subject['values']  = sub_list
        self.cb_exam_sub['values'] = sub_list
        if sub_list:
            if not self.cb_subject.get():
                self.cb_subject.set(sub_list[0])
            if not self.cb_exam_sub.get():
                self.cb_exam_sub.set(sub_list[0])

        # Timetable tree
        for item in self.tt_tree.get_children():
            self.tt_tree.delete(item)
        for s in queries.get_all_timetable_slots(self.conn):
            self.tt_tree.insert('', 'end', iid=str(s['slot_id']), values=(
                s['slot_id'],
                f"Day {s['day_order']}",
                f"{s['start_time']} – {s['end_time']}",
                s['subject_code'] or '',
                s['subject_name'],
                s['section'] or '',
            ))

        # Exam tree
        for item in self.ex_tree.get_children():
            self.ex_tree.delete(item)
        for e in queries.get_all_exams(self.conn):
            self.ex_tree.insert('', 'end', iid=str(e['exam_id']), values=(
                e['exam_id'],
                e['exam_date'],
                f"{e['start_time']} – {e['end_time']}",
                e['subject_code'] or '',
                e['subject_name'],
            ))

    # ── Timetable actions ─────────────────────────────────────────────────────

    def _on_tt_select(self, event):
        sel = self.tt_tree.selection()
        if not sel:
            return
        slot = queries.get_timetable_slot_by_id(self.conn, int(sel[0]))
        if not slot:
            return
        self.selected_slot_id = slot['slot_id']
        for name, sid in self.subject_map.items():
            if sid == slot['subject_id']:
                self.cb_subject.set(name)
                break
        self.cb_day_order.set(DO_INT_TO_LABEL.get(slot['day_order'], "Day 1"))
        self._set_entry(self.entry_start, slot['start_time'])
        self._set_entry(self.entry_end,   slot['end_time'])
        self._set_entry(self.entry_sec,   slot['section'] or '')

    def _clear_tt_form(self):
        self.selected_slot_id = None
        self.tt_tree.selection_remove(self.tt_tree.selection())
        self._set_entry(self.entry_start, "09:45")
        self._set_entry(self.entry_end,   "10:35")
        self._set_entry(self.entry_sec,   "TP 704")
        self.cb_day_order.set("Day 1")

    def _save_slot(self):
        sub_name = self.cb_subject.get()
        if sub_name not in self.subject_map:
            messagebox.showwarning("Validation", "Select a valid subject.")
            return
        do_label = self.cb_day_order.get()
        do = DO_LABEL_TO_INT.get(do_label)
        if not do:
            messagebox.showwarning("Validation", "Select a Day Order.")
            return
        start = self.entry_start.get().strip()
        end   = self.entry_end.get().strip()
        sec   = self.entry_sec.get().strip()
        if not start or not end:
            messagebox.showwarning("Validation", "Start and End times are required.")
            return
        sub_id = self.subject_map[sub_name]
        if self.selected_slot_id:
            queries.update_timetable_slot(self.conn, self.selected_slot_id, sub_id, do, start, end, sec)
        else:
            queries.insert_timetable_slot(self.conn, sub_id, do, start, end, sec)
        self._clear_tt_form()
        self.refresh()
        self._auto_rescan()

    def _delete_slot(self):
        if not self.selected_slot_id:
            messagebox.showinfo("Info", "Select a class to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete this timetable slot?"):
            queries.delete_timetable_slot(self.conn, self.selected_slot_id)
            self._clear_tt_form()
            self.refresh()
            self._auto_rescan()

    # ── Exam actions ──────────────────────────────────────────────────────────

    def _on_ex_select(self, event):
        sel = self.ex_tree.selection()
        if not sel:
            return
        exam = queries.get_exam_by_id(self.conn, int(sel[0]))
        if not exam:
            return
        self.selected_exam_id = exam['exam_id']
        for name, sid in self.subject_map.items():
            if sid == exam['subject_id']:
                self.cb_exam_sub.set(name)
                break
        self._set_entry(self.entry_exam_date,  exam['exam_date'])
        self._set_entry(self.entry_exam_start, exam['start_time'])
        self._set_entry(self.entry_exam_end,   exam['end_time'])

    def _clear_exam_form(self):
        self.selected_exam_id = None
        self.ex_tree.selection_remove(self.ex_tree.selection())
        self.entry_exam_date.delete(0, 'end')
        self._set_entry(self.entry_exam_start, "09:00")
        self._set_entry(self.entry_exam_end,   "12:00")

    def _save_exam(self):
        sub_name = self.cb_exam_sub.get()
        if sub_name not in self.subject_map:
            messagebox.showwarning("Validation", "Select a valid subject.")
            return
        edate = self.entry_exam_date.get().strip()
        start = self.entry_exam_start.get().strip()
        end   = self.entry_exam_end.get().strip()
        if not edate or not start or not end:
            messagebox.showwarning("Validation", "All fields are required.")
            return
        sub_id = self.subject_map[sub_name]
        if self.selected_exam_id:
            queries.update_exam(self.conn, self.selected_exam_id, sub_id, edate, start, end)
        else:
            queries.insert_exam(self.conn, sub_id, edate, start, end)
        self._clear_exam_form()
        self.refresh()
        self._auto_rescan()

    def _delete_exam(self):
        if not self.selected_exam_id:
            messagebox.showinfo("Info", "Select an exam to delete.")
            return
        if messagebox.askyesno("Confirm", "Delete this exam?"):
            queries.delete_exam(self.conn, self.selected_exam_id)
            self._clear_exam_form()
            self.refresh()
            self._auto_rescan()

    # ── Clash scanning ────────────────────────────────────────────────────────

    def _auto_rescan(self):
        slots  = queries.get_all_timetable_slots(self.conn)
        exams  = queries.get_all_exams(self.conn)
        pivot_date = queries.get_setting(self.conn, 'pivot_date')
        pivot_do   = int(queries.get_setting(self.conn, 'pivot_day_order', '1'))
        clashes = detect_clashes(slots, exams, pivot_date, pivot_do)
        queries.save_clashes(self.conn, clashes)
        if self.on_clash_detected:
            self.on_clash_detected(len(clashes))

    def _scan_clashes(self):
        self._auto_rescan()
        clashes = queries.get_all_clashes(self.conn)
        if clashes:
            messagebox.showwarning("Conflicts Detected",
                f"Found {len(clashes)} conflict(s)!\n"
                "See the Clash Report screen for details and resolution advice.")
        else:
            messagebox.showinfo("No Clashes", "Zero conflicts found — your schedule is clean!")

    # ── Utility ───────────────────────────────────────────────────────────────

    def _set_entry(self, widget, value):
        widget.delete(0, 'end')
        widget.insert(0, str(value))
