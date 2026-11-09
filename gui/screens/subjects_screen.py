"""
Subjects & Topics Screen for ClashBoard.
Enables full management of subjects (difficulty, credits) and expandable topics.
Topic priority is interactively adjusted via ttk.Scale (1 to 5) with live urgency preview.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from db import queries
from services.scheduler import compute_urgency
from gui.styles import BG_COLOR, CARD_BG, ACCENT_COLOR, TEXT_COLOR, MUTED_TEXT, BORDER_COLOR


class SubjectsScreen(ttk.Frame):
    def __init__(self, parent, conn, on_data_change=None):
        super().__init__(parent, style='TFrame')
        self.conn = conn
        self.on_data_change = on_data_change

        self.selected_subject_id = None
        self.selected_topic_id = None

        self._build_ui()
        self.refresh_subjects()

    def _build_ui(self):
        # Header banner
        header = ttk.Frame(self, style='TFrame')
        header.pack(fill='x', padx=20, pady=(15, 10))

        ttk.Label(
            header,
            text="Subjects & Revision Topics",
            style='Header.TLabel'
        ).pack(side='left')

        ttk.Label(
            header,
            text="Configure subject difficulty and topic priorities for adaptive scheduling",
            style='Muted.TLabel'
        ).pack(side='left', padx=(15, 0), pady=(4, 0))

        # Main horizontal split
        split_frame = ttk.Frame(self, style='TFrame')
        split_frame.pack(fill='both', expand=True, padx=20, pady=(0, 15))

        # ==========================================
        # LEFT PANE: SUBJECTS
        # ==========================================
        left_pane = ttk.LabelFrame(split_frame, text=" Enrolled Subjects ", padding=10)
        left_pane.pack(side='left', fill='both', expand=True, padx=(0, 8))

        # Subjects Treeview
        tree_frame = ttk.Frame(left_pane, style='TFrame')
        tree_frame.pack(fill='both', expand=True)

        cols = ('id', 'code', 'name', 'diff', 'credits')
        self.sub_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', selectmode='browse')
        self.sub_tree.heading('id', text='ID')
        self.sub_tree.heading('code', text='Code')
        self.sub_tree.heading('name', text='Subject Name')
        self.sub_tree.heading('diff', text='Diff (1-5)')
        self.sub_tree.heading('credits', text='Credits')

        self.sub_tree.column('id', width=35, anchor='center')
        self.sub_tree.column('code', width=70, anchor='center')
        self.sub_tree.column('name', width=200, anchor='w')
        self.sub_tree.column('diff', width=70, anchor='center')
        self.sub_tree.column('credits', width=60, anchor='center')

        sub_scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.sub_tree.yview)
        self.sub_tree.configure(yscrollcommand=sub_scroll.set)
        self.sub_tree.pack(side='left', fill='both', expand=True)
        sub_scroll.pack(side='right', fill='y')

        self.sub_tree.bind('<<TreeviewSelect>>', self._on_select_subject)

        # Subject Form
        sub_form = ttk.LabelFrame(left_pane, text=" Subject Details ", padding=10)
        sub_form.pack(fill='x', pady=(10, 0))

        grid_f = ttk.Frame(sub_form, style='TFrame')
        grid_f.pack(fill='x')

        ttk.Label(grid_f, text="Code:").grid(row=0, column=0, sticky='w', pady=3)
        self.entry_sub_code = ttk.Entry(grid_f, width=12)
        self.entry_sub_code.grid(row=0, column=1, sticky='w', padx=5, pady=3)

        ttk.Label(grid_f, text="Name:").grid(row=0, column=2, sticky='w', padx=(10, 0), pady=3)
        self.entry_sub_name = ttk.Entry(grid_f, width=22)
        self.entry_sub_name.grid(row=0, column=3, sticky='w', padx=5, pady=3)

        ttk.Label(grid_f, text="Difficulty:").grid(row=1, column=0, sticky='w', pady=3)
        self.cb_sub_diff = ttk.Combobox(grid_f, values=['1 (Very Easy)', '2 (Easy)', '3 (Medium)', '4 (Hard)', '5 (Very Hard)'], state='readonly', width=14)
        self.cb_sub_diff.set('3 (Medium)')
        self.cb_sub_diff.grid(row=1, column=1, sticky='w', padx=5, pady=3)

        ttk.Label(grid_f, text="Credits:").grid(row=1, column=2, sticky='w', padx=(10, 0), pady=3)
        self.entry_sub_credits = ttk.Entry(grid_f, width=10)
        self.entry_sub_credits.insert(0, "4")
        self.entry_sub_credits.grid(row=1, column=3, sticky='w', padx=5, pady=3)

        sub_btns = ttk.Frame(sub_form, style='TFrame')
        sub_btns.pack(fill='x', pady=(8, 0))

        ttk.Button(sub_btns, text="Save Subject", style='Accent.TButton', command=self._save_subject).pack(side='left', padx=3)
        ttk.Button(sub_btns, text="Delete", style='Danger.TButton', command=self._delete_subject).pack(side='left', padx=3)
        ttk.Button(sub_btns, text="Clear", style='Secondary.TButton', command=self._clear_sub_form).pack(side='left', padx=3)

        # ==========================================
        # RIGHT PANE: TOPICS FOR SELECTED SUBJECT
        # ==========================================
        right_pane = ttk.LabelFrame(split_frame, text=" Revision Topics ", padding=10)
        right_pane.pack(side='right', fill='both', expand=True, padx=(8, 0))

        # Selected Subject Banner
        self.lbl_selected_banner = ttk.Label(
            right_pane,
            text="← Select a subject on the left to view and edit its topics",
            font=('Segoe UI', 10, 'italic'),
            foreground=ACCENT_COLOR
        )
        self.lbl_selected_banner.pack(anchor='w', pady=(0, 8))

        # Topics Treeview
        top_tree_frame = ttk.Frame(right_pane, style='TFrame')
        top_tree_frame.pack(fill='both', expand=True)

        top_cols = ('id', 'name', 'hours', 'priority', 'exam_date')
        self.top_tree = ttk.Treeview(top_tree_frame, columns=top_cols, show='headings', selectmode='browse')
        self.top_tree.heading('id', text='ID')
        self.top_tree.heading('name', text='Topic Name')
        self.top_tree.heading('hours', text='Est. Hours')
        self.top_tree.heading('priority', text='Priority (1-5)')
        self.top_tree.heading('exam_date', text='Exam Date')

        self.top_tree.column('id', width=35, anchor='center')
        self.top_tree.column('name', width=220, anchor='w')
        self.top_tree.column('hours', width=75, anchor='center')
        self.top_tree.column('priority', width=90, anchor='center')
        self.top_tree.column('exam_date', width=95, anchor='center')

        top_scroll = ttk.Scrollbar(top_tree_frame, orient='vertical', command=self.top_tree.yview)
        self.top_tree.configure(yscrollcommand=top_scroll.set)
        self.top_tree.pack(side='left', fill='both', expand=True)
        top_scroll.pack(side='right', fill='y')

        self.top_tree.bind('<<TreeviewSelect>>', self._on_select_topic)

        # Topic Form
        top_form = ttk.LabelFrame(right_pane, text=" Add / Edit Revision Topic ", padding=10)
        top_form.pack(fill='x', pady=(10, 0))

        t_grid = ttk.Frame(top_form, style='TFrame')
        t_grid.pack(fill='x')

        ttk.Label(t_grid, text="Topic Name:").grid(row=0, column=0, sticky='w', pady=4)
        self.entry_top_name = ttk.Entry(t_grid, width=32)
        self.entry_top_name.grid(row=0, column=1, sticky='w', padx=5, pady=4)

        ttk.Label(t_grid, text="Estimated Hours:").grid(row=1, column=0, sticky='w', pady=4)
        self.entry_top_hours = ttk.Entry(t_grid, width=12)
        self.entry_top_hours.insert(0, "2.5")
        self.entry_top_hours.grid(row=1, column=1, sticky='w', padx=5, pady=4)

        # Priority Slider with live feedback label
        ttk.Label(t_grid, text="Priority (1-5):").grid(row=2, column=0, sticky='w', pady=4)
        
        slider_box = ttk.Frame(t_grid, style='TFrame')
        slider_box.grid(row=2, column=1, sticky='w', padx=5, pady=4)

        self.scale_priority = ttk.Scale(
            slider_box,
            from_=1,
            to=5,
            orient='horizontal',
            length=160,
            command=self._on_priority_slider_change
        )
        self.scale_priority.set(3)
        self.scale_priority.pack(side='left')

        self.lbl_prio_val = ttk.Label(slider_box, text="3 (Medium)", font=('Segoe UI', 9, 'bold'), foreground=ACCENT_COLOR)
        self.lbl_prio_val.pack(side='left', padx=(8, 0))

        top_btns = ttk.Frame(top_form, style='TFrame')
        top_btns.pack(fill='x', pady=(8, 0))

        self.btn_save_topic = ttk.Button(top_btns, text="Save Topic", style='Accent.TButton', command=self._save_topic)
        self.btn_save_topic.pack(side='left', padx=3)

        self.btn_del_topic = ttk.Button(top_btns, text="Delete", style='Danger.TButton', command=self._delete_topic)
        self.btn_del_topic.pack(side='left', padx=3)

        self.btn_clear_topic = ttk.Button(top_btns, text="Clear", style='Secondary.TButton', command=self._clear_topic_form)
        self.btn_clear_topic.pack(side='left', padx=3)

    def _on_priority_slider_change(self, val):
        prio = int(round(float(val)))
        label_map = {
            1: "1 (Low)",
            2: "2 (Below Avg)",
            3: "3 (Medium)",
            4: "4 (High)",
            5: "5 (Critical)"
        }
        self.lbl_prio_val.config(text=label_map.get(prio, f"{prio}"))

    def refresh_subjects(self):
        """Reloads subjects list."""
        for item in self.sub_tree.get_children():
            self.sub_tree.delete(item)

        subjects = queries.get_all_subjects(self.conn)
        for s in subjects:
            self.sub_tree.insert(
                '',
                'end',
                iid=str(s['subject_id']),
                values=(
                    s['subject_id'],
                    s['code'] or '',
                    s['name'],
                    s['difficulty_level'] or 3,
                    s['credits'] or 3
                )
            )

        if self.selected_subject_id:
            # Re-select if still exists
            if self.sub_tree.exists(str(self.selected_subject_id)):
                self.sub_tree.selection_set(str(self.selected_subject_id))
                self.refresh_topics()
            else:
                self.selected_subject_id = None
                self._clear_sub_form()
                self._clear_topic_form()
        elif subjects:
            # Auto-select first subject
            first_id = subjects[0]['subject_id']
            self.sub_tree.selection_set(str(first_id))
            self.selected_subject_id = first_id
            self._load_subject_to_form(first_id)
            self.refresh_topics()

    def refresh_topics(self):
        """Reloads topics for the currently selected subject."""
        for item in self.top_tree.get_children():
            self.top_tree.delete(item)

        if not self.selected_subject_id:
            self.lbl_selected_banner.config(text="← Select a subject on the left to view its topics")
            return

        sub = queries.get_subject_by_id(self.conn, self.selected_subject_id)
        if sub:
            self.lbl_selected_banner.config(
                text=f"Topics for: {sub['code']} - {sub['name']} (Difficulty: {sub['difficulty_level']}/5)"
            )

        topics = queries.get_topics_by_subject(self.conn, self.selected_subject_id)
        for t in topics:
            self.top_tree.insert(
                '',
                'end',
                iid=str(t['topic_id']),
                values=(
                    t['topic_id'],
                    t['topic_name'],
                    f"{t['estimated_hours']} hrs",
                    f"{t['priority']}/5",
                    t['exam_date'] or 'No Exam'
                )
            )

    def _on_select_subject(self, event):
        sel = self.sub_tree.selection()
        if not sel:
            return
        sub_id = int(sel[0])
        self.selected_subject_id = sub_id
        self._load_subject_to_form(sub_id)
        self._clear_topic_form()
        self.refresh_topics()

    def _load_subject_to_form(self, sub_id):
        sub = queries.get_subject_by_id(self.conn, sub_id)
        if not sub:
            return
        self.entry_sub_code.delete(0, 'end')
        self.entry_sub_code.insert(0, sub['code'] or '')
        self.entry_sub_name.delete(0, 'end')
        self.entry_sub_name.insert(0, sub['name'])

        diff = sub['difficulty_level'] or 3
        diff_str = {
            1: '1 (Very Easy)',
            2: '2 (Easy)',
            3: '3 (Medium)',
            4: '4 (Hard)',
            5: '5 (Very Hard)'
        }.get(diff, '3 (Medium)')
        self.cb_sub_diff.set(diff_str)

        self.entry_sub_credits.delete(0, 'end')
        self.entry_sub_credits.insert(0, str(sub['credits'] or 3))

    def _clear_sub_form(self):
        self.selected_subject_id = None
        self.sub_tree.selection_remove(self.sub_tree.selection())
        self.entry_sub_code.delete(0, 'end')
        self.entry_sub_name.delete(0, 'end')
        self.cb_sub_diff.set('3 (Medium)')
        self.entry_sub_credits.delete(0, 'end')
        self.entry_sub_credits.insert(0, "4")
        self.refresh_topics()

    def _save_subject(self):
        code = self.entry_sub_code.get().strip()
        name = self.entry_sub_name.get().strip()
        if not name:
            messagebox.showwarning("Validation Error", "Subject Name is required.")
            return

        diff_str = self.cb_sub_diff.get()
        diff = int(diff_str.split()[0]) if diff_str else 3

        try:
            credits_val = int(self.entry_sub_credits.get().strip() or 3)
        except ValueError:
            credits_val = 3

        if self.selected_subject_id:
            queries.update_subject(self.conn, self.selected_subject_id, name, code, diff, credits_val)
        else:
            self.selected_subject_id = queries.insert_subject(self.conn, name, code, diff, credits_val)

        self.refresh_subjects()
        if self.on_data_change:
            self.on_data_change()

    def _delete_subject(self):
        if not self.selected_subject_id:
            messagebox.showinfo("Select Subject", "Please select a subject to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Deleting this subject will also delete its timetable slots, exams, and topics. Continue?"):
            queries.delete_subject(self.conn, self.selected_subject_id)
            self._clear_sub_form()
            self.refresh_subjects()
            if self.on_data_change:
                self.on_data_change()

    def _on_select_topic(self, event):
        sel = self.top_tree.selection()
        if not sel:
            return
        top_id = int(sel[0])
        topic = queries.get_topic_by_id(self.conn, top_id)
        if not topic:
            return
        self.selected_topic_id = top_id
        self.entry_top_name.delete(0, 'end')
        self.entry_top_name.insert(0, topic['topic_name'])
        self.entry_top_hours.delete(0, 'end')
        self.entry_top_hours.insert(0, str(topic['estimated_hours']))
        prio = topic['priority'] or 3
        self.scale_priority.set(prio)
        self._on_priority_slider_change(prio)

    def _clear_topic_form(self):
        self.selected_topic_id = None
        self.top_tree.selection_remove(self.top_tree.selection())
        self.entry_top_name.delete(0, 'end')
        self.entry_top_hours.delete(0, 'end')
        self.entry_top_hours.insert(0, "2.0")
        self.scale_priority.set(3)
        self._on_priority_slider_change(3)

    def _save_topic(self):
        if not self.selected_subject_id:
            messagebox.showwarning("No Subject", "Please select or create a subject first before adding topics.")
            return

        name = self.entry_top_name.get().strip()
        if not name:
            messagebox.showwarning("Validation Error", "Topic name is required.")
            return

        try:
            hours = float(self.entry_top_hours.get().strip())
            if hours <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("Validation Error", "Estimated hours must be a positive number.")
            return

        prio = int(round(self.scale_priority.get()))

        if self.selected_topic_id:
            queries.update_topic(self.conn, self.selected_topic_id, self.selected_subject_id, name, hours, prio)
        else:
            queries.insert_topic(self.conn, self.selected_subject_id, name, hours, prio)

        self._clear_topic_form()
        self.refresh_topics()
        if self.on_data_change:
            self.on_data_change()

    def _delete_topic(self):
        if not self.selected_topic_id:
            messagebox.showinfo("Select Topic", "Please select a topic to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this topic and its planned sessions?"):
            queries.delete_topic(self.conn, self.selected_topic_id)
            self._clear_topic_form()
            self.refresh_topics()
            if self.on_data_change:
                self.on_data_change()

