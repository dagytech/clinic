

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import sqlite3
import os
from datetime import datetime, date
import re

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "clinic.db")

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dob TEXT,
            gender TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            reason TEXT,
            doctor TEXT,
            status TEXT DEFAULT 'Scheduled',
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            appointment_id INTEGER,
            treatment_name TEXT NOT NULL,
            tooth_number TEXT,
            cost REAL DEFAULT 0,
            date TEXT,
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            total REAL DEFAULT 0,
            paid REAL DEFAULT 0,
            status TEXT DEFAULT 'Unpaid',
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            description TEXT,
            quantity INTEGER DEFAULT 1,
            unit_price REAL DEFAULT 0,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id)
        )
    """)

    # Seed sample data if empty
    c.execute("SELECT COUNT(*) FROM patients")
    if c.fetchone()[0] == 0:
        sample_patients = [
            ("Alice Mwamba", "1990-03-15", "Female", "+255 712 000 001", "alice@email.com", "Mikocheni, DSM"),
            ("John Banda", "1985-07-22", "Male", "+255 754 000 002", "john@email.com", "Kinondoni, DSM"),
            ("Grace Tembo", "2000-11-08", "Female", "+255 767 000 003", "grace@email.com", "Ilala, DSM"),
        ]
        c.executemany("INSERT INTO patients (name,dob,gender,phone,email,address) VALUES (?,?,?,?,?,?)", sample_patients)
        today = date.today().isoformat()
        c.execute("INSERT INTO appointments (patient_id,date,time,reason,doctor,status) VALUES (1,?,?,?,?,?)",
                  (today, "09:00", "Routine Checkup", "Dr. Salim", "Scheduled"))
        c.execute("INSERT INTO appointments (patient_id,date,time,reason,doctor,status) VALUES (2,?,?,?,?,?)",
                  (today, "10:30", "Tooth Extraction", "Dr. Salim", "Confirmed"))
        c.execute("INSERT INTO treatments (patient_id,treatment_name,tooth_number,cost,date) VALUES (1,'Scaling & Polishing','All',50000,?)", (today,))
        c.execute("INSERT INTO treatments (patient_id,treatment_name,tooth_number,cost,date) VALUES (2,'Extraction','#18',80000,?)", (today,))
        c.execute("INSERT INTO invoices (patient_id,date,total,paid,status) VALUES (1,?,50000,0,'Unpaid')", (today,))
        c.execute("INSERT INTO invoice_items (invoice_id,description,quantity,unit_price) VALUES (1,'Scaling & Polishing',1,50000)")

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────

class DentalApp(tb.Window):
    def __init__(self):
        super().__init__(themename="litera")
        self.title("🦷 DentaCare – Clinic Management System")
        self.geometry("1200x720")
        self.minsize(1000, 600)
        self._build_ui()

    def _build_ui(self):
        # ── Sidebar ──
        sidebar = tb.Frame(self, bootstyle="dark", width=200)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        tb.Label(sidebar, text="🦷 DentaCare", font=("Segoe UI", 14, "bold"),
                 bootstyle="inverse-dark", foreground="#38BDF8").pack(pady=(20, 4), padx=16, anchor="w")
        tb.Label(sidebar, text="Clinic Management", font=("Segoe UI", 8),
                 bootstyle="inverse-dark", foreground="#94A3B8").pack(padx=16, anchor="w")
        ttk.Separator(sidebar).pack(fill=X, pady=12, padx=10)

        self.nav_buttons = []
        nav_items = [
            ("📊  Dashboard",    self._show_dashboard),
            ("👥  Patients",     self._show_patients),
            ("📅  Appointments", self._show_appointments),
            ("🔬  Treatments",   self._show_treatments),
            ("💳  Billing",      self._show_billing),
        ]
        self.active_nav = tk.StringVar(value="📊  Dashboard")
        for label, cmd in nav_items:
            btn = tb.Button(sidebar, text=label, bootstyle="dark", width=22,
                            command=lambda l=label, c=cmd: self._nav_click(l, c))
            btn.pack(pady=2, padx=10)
            self.nav_buttons.append((label, btn))

        # ── Main Content ──
        self.content = tb.Frame(self)
        self.content.pack(side=LEFT, fill=BOTH, expand=True)

        # Header bar
        self.header = tb.Frame(self.content, bootstyle="light", height=56)
        self.header.pack(fill=X)
        self.header.pack_propagate(False)
        self.page_title = tb.Label(self.header, text="Dashboard",
                                   font=("Segoe UI", 14, "bold"), bootstyle="dark")
        self.page_title.pack(side=LEFT, padx=20, pady=14)
        self.today_label = tb.Label(self.header,
                                    text=datetime.now().strftime("%A, %d %B %Y"),
                                    font=("Segoe UI", 9), bootstyle="secondary")
        self.today_label.pack(side=RIGHT, padx=20, pady=14)

        self.page_frame = tb.Frame(self.content)
        self.page_frame.pack(fill=BOTH, expand=True, padx=16, pady=12)

        self._show_dashboard()

    def _nav_click(self, label, cmd):
        self.active_nav.set(label)
        cmd()

    def _clear_page(self, title=""):
        for w in self.page_frame.winfo_children():
            w.destroy()
        self.page_title.config(text=title)

    # ─────────────────────────────────────────
    # DASHBOARD
    # ─────────────────────────────────────────

    def _show_dashboard(self):
        self._clear_page("Dashboard")
        f = self.page_frame

        conn = get_conn()
        c = conn.cursor()
        today = date.today().isoformat()

        total_patients  = c.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        today_appts     = c.execute("SELECT COUNT(*) FROM appointments WHERE date=?", (today,)).fetchone()[0]
        pending_invoices= c.execute("SELECT COUNT(*) FROM invoices WHERE status='Unpaid'").fetchone()[0]
        revenue_today   = c.execute("SELECT COALESCE(SUM(paid),0) FROM invoices WHERE date=?", (today,)).fetchone()[0]
        conn.close()

        # Stat cards row
        cards_frame = tb.Frame(f)
        cards_frame.pack(fill=X, pady=(0, 16))

        stats = [
            ("👥 Total Patients",     str(total_patients),   "primary"),
            ("📅 Today's Appointments", str(today_appts),    "success"),
            ("💳 Unpaid Invoices",    str(pending_invoices), "warning"),
            ("💰 Revenue Today",      f"TZS {revenue_today:,.0f}", "info"),
        ]
        for i, (label, value, style) in enumerate(stats):
            card = tb.Frame(cards_frame, bootstyle=f"{style}", padding=16)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            cards_frame.columnconfigure(i, weight=1)
            tb.Label(card, text=value, font=("Segoe UI", 22, "bold"),
                     bootstyle=f"inverse-{style}").pack(anchor="w")
            tb.Label(card, text=label, font=("Segoe UI", 9),
                     bootstyle=f"inverse-{style}").pack(anchor="w")

        # Two columns: today's appointments + recent patients
        cols = tb.Frame(f)
        cols.pack(fill=BOTH, expand=True)
        cols.columnconfigure(0, weight=3)
        cols.columnconfigure(1, weight=2)

        # Today's appointments table
        appt_frame = tb.LabelFrame(cols, text=" Today's Appointments ", bootstyle="primary", padding=10)
        appt_frame.grid(row=0, column=0, padx=(0,8), sticky="nsew")

        cols_def = ("Patient", "Time", "Reason", "Doctor", "Status")
        tree = ttk.Treeview(appt_frame, columns=cols_def, show="headings", height=10)
        for col in cols_def:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.pack(fill=BOTH, expand=True)

        conn = get_conn()
        rows = conn.execute("""
            SELECT p.name, a.time, a.reason, a.doctor, a.status
            FROM appointments a JOIN patients p ON a.patient_id=p.id
            WHERE a.date=? ORDER BY a.time
        """, (today,)).fetchall()
        conn.close()
        for row in rows:
            tree.insert("", END, values=row)

        # Recent patients
        pat_frame = tb.LabelFrame(cols, text=" Recent Patients ", bootstyle="info", padding=10)
        pat_frame.grid(row=0, column=1, sticky="nsew")

        ptree = ttk.Treeview(pat_frame, columns=("Name", "Phone"), show="headings", height=10)
        for col in ("Name", "Phone"):
            ptree.heading(col, text=col)
        ptree.pack(fill=BOTH, expand=True)

        conn = get_conn()
        prows = conn.execute("SELECT name, phone FROM patients ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        for row in prows:
            ptree.insert("", END, values=row)

    # ─────────────────────────────────────────
    # PATIENTS
    # ─────────────────────────────────────────

    def _show_patients(self):
        self._clear_page("Patients")
        f = self.page_frame

        # Toolbar
        toolbar = tb.Frame(f)
        toolbar.pack(fill=X, pady=(0, 8))
        tb.Button(toolbar, text="+ New Patient", bootstyle="success",
                  command=self._patient_form).pack(side=LEFT)
        self._pat_search = tb.Entry(toolbar, width=28)
        self._pat_search.pack(side=RIGHT, padx=(4,0))
        tb.Label(toolbar, text="Search:").pack(side=RIGHT)
        self._pat_search.bind("<KeyRelease>", lambda e: self._load_patients())

        # Table
        cols = ("ID", "Name", "DOB", "Gender", "Phone", "Email")
        self.pat_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        widths = [40, 180, 100, 70, 130, 180]
        for col, w in zip(cols, widths):
            self.pat_tree.heading(col, text=col, command=lambda c=col: self._sort_tree(self.pat_tree, c))
            self.pat_tree.column(col, width=w)
        scroll = ttk.Scrollbar(f, orient=VERTICAL, command=self.pat_tree.yview)
        self.pat_tree.configure(yscrollcommand=scroll.set)
        self.pat_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=LEFT, fill=Y)

        self.pat_tree.bind("<Double-1>", lambda e: self._patient_form(edit=True))
        self.pat_tree.bind("<Delete>", lambda e: self._delete_patient())
        self._load_patients()

        tb.Label(f, text="Double-click to edit • Delete key to remove", bootstyle="secondary",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=4)

    def _load_patients(self):
        query = getattr(self, "_pat_search", None)
        term = f"%{query.get()}%" if query else "%%"
        conn = get_conn()
        rows = conn.execute(
            "SELECT id,name,dob,gender,phone,email FROM patients WHERE name LIKE ? OR phone LIKE ? ORDER BY name",
            (term, term)
        ).fetchall()
        conn.close()
        self.pat_tree.delete(*self.pat_tree.get_children())
        for row in rows:
            self.pat_tree.insert("", END, values=row)

    def _patient_form(self, edit=False):
        record = None
        if edit:
            sel = self.pat_tree.selection()
            if not sel:
                return
            record = self.pat_tree.item(sel[0])["values"]

        dlg = tb.Toplevel(self)
        dlg.title("Edit Patient" if edit else "New Patient")
        dlg.geometry("420x420")
        dlg.grab_set()

        fields = [("Full Name*", "name"), ("Date of Birth (YYYY-MM-DD)", "dob"),
                  ("Gender", "gender"), ("Phone", "phone"), ("Email", "email"), ("Address", "address")]
        entries = {}

        for i, (label, key) in enumerate(fields):
            tb.Label(dlg, text=label).grid(row=i, column=0, padx=20, pady=6, sticky="w")
            if key == "gender":
                var = tk.StringVar()
                cb = ttk.Combobox(dlg, textvariable=var, values=["Male", "Female", "Other"], width=28)
                cb.grid(row=i, column=1, padx=20, pady=6)
                entries[key] = var
            else:
                e = tb.Entry(dlg, width=30)
                e.grid(row=i, column=1, padx=20, pady=6)
                entries[key] = e

        if edit and record:
            vals = list(record)
            for j, (_, key) in enumerate(fields):
                val = vals[j+1] if j+1 < len(vals) else ""
                ent = entries[key]
                if isinstance(ent, tk.StringVar):
                    ent.set(val or "")
                else:
                    ent.delete(0, END)
                    ent.insert(0, val or "")

        def save():
            name = entries["name"].get().strip() if hasattr(entries["name"], "get") else ""
            if not name:
                messagebox.showerror("Validation", "Name is required.", parent=dlg)
                return
            data = {k: (v.get() if isinstance(v, tk.StringVar) else v.get()) for k, v in entries.items()}
            conn = get_conn()
            if edit:
                conn.execute("""UPDATE patients SET name=?,dob=?,gender=?,phone=?,email=?,address=?
                                WHERE id=?""",
                             (data["name"], data["dob"], data["gender"], data["phone"],
                              data["email"], data["address"], record[0]))
            else:
                conn.execute("INSERT INTO patients (name,dob,gender,phone,email,address) VALUES (?,?,?,?,?,?)",
                             (data["name"], data["dob"], data["gender"], data["phone"], data["email"], data["address"]))
            conn.commit()
            conn.close()
            dlg.destroy()
            self._load_patients()

        tb.Button(dlg, text="Save", bootstyle="success", command=save).grid(row=len(fields), column=0, columnspan=2, pady=16)

    def _delete_patient(self):
        sel = self.pat_tree.selection()
        if not sel:
            return
        record = self.pat_tree.item(sel[0])["values"]
        if messagebox.askyesno("Confirm", f"Delete patient '{record[1]}'? This cannot be undone."):
            conn = get_conn()
            conn.execute("DELETE FROM patients WHERE id=?", (record[0],))
            conn.commit()
            conn.close()
            self._load_patients()

    # ─────────────────────────────────────────
    # APPOINTMENTS
    # ─────────────────────────────────────────

    def _show_appointments(self):
        self._clear_page("Appointments")
        f = self.page_frame

        toolbar = tb.Frame(f)
        toolbar.pack(fill=X, pady=(0, 8))
        tb.Button(toolbar, text="+ New Appointment", bootstyle="success",
                  command=self._appointment_form).pack(side=LEFT, padx=(0, 6))
        tb.Button(toolbar, text="✓ Mark Completed", bootstyle="info",
                  command=lambda: self._update_appt_status("Completed")).pack(side=LEFT, padx=(0,6))
        tb.Button(toolbar, text="✗ Cancel", bootstyle="warning",
                  command=lambda: self._update_appt_status("Cancelled")).pack(side=LEFT)

        # Date filter
        tb.Label(toolbar, text="Date filter:").pack(side=RIGHT, padx=(8,4))
        self._appt_date_filter = tb.Entry(toolbar, width=14)
        self._appt_date_filter.pack(side=RIGHT)
        self._appt_date_filter.insert(0, date.today().isoformat())
        self._appt_date_filter.bind("<KeyRelease>", lambda e: self._load_appointments())

        cols = ("ID", "Patient", "Date", "Time", "Reason", "Doctor", "Status")
        self.appt_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        widths = [40, 160, 100, 70, 180, 120, 100]
        for col, w in zip(cols, widths):
            self.appt_tree.heading(col, text=col)
            self.appt_tree.column(col, width=w)
        scroll = ttk.Scrollbar(f, orient=VERTICAL, command=self.appt_tree.yview)
        self.appt_tree.configure(yscrollcommand=scroll.set)
        self.appt_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=LEFT, fill=Y)
        self.appt_tree.tag_configure("Completed", foreground="#22c55e")
        self.appt_tree.tag_configure("Cancelled", foreground="#ef4444")
        self.appt_tree.bind("<Double-1>", lambda e: self._appointment_form(edit=True))
        self._load_appointments()

    def _load_appointments(self):
        date_filter = getattr(self, "_appt_date_filter", None)
        term = date_filter.get().strip() if date_filter else ""
        conn = get_conn()
        if term:
            rows = conn.execute("""
                SELECT a.id, p.name, a.date, a.time, a.reason, a.doctor, a.status
                FROM appointments a JOIN patients p ON a.patient_id=p.id
                WHERE a.date=? ORDER BY a.time
            """, (term,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT a.id, p.name, a.date, a.time, a.reason, a.doctor, a.status
                FROM appointments a JOIN patients p ON a.patient_id=p.id
                ORDER BY a.date DESC, a.time
            """).fetchall()
        conn.close()
        self.appt_tree.delete(*self.appt_tree.get_children())
        for row in rows:
            tag = row[6] if row[6] in ("Completed", "Cancelled") else ""
            self.appt_tree.insert("", END, values=row, tags=(tag,))

    def _update_appt_status(self, status):
        sel = self.appt_tree.selection()
        if not sel:
            return
        appt_id = self.appt_tree.item(sel[0])["values"][0]
        conn = get_conn()
        conn.execute("UPDATE appointments SET status=? WHERE id=?", (status, appt_id))
        conn.commit()
        conn.close()
        self._load_appointments()

    def _appointment_form(self, edit=False):
        record = None
        if edit:
            sel = self.appt_tree.selection()
            if not sel:
                return
            record = self.appt_tree.item(sel[0])["values"]

        dlg = tb.Toplevel(self)
        dlg.title("Edit Appointment" if edit else "New Appointment")
        dlg.geometry("440x460")
        dlg.grab_set()

        # Patient dropdown
        conn = get_conn()
        patients = conn.execute("SELECT id, name FROM patients ORDER BY name").fetchall()
        conn.close()
        pat_map = {p[1]: p[0] for p in patients}
        pat_names = list(pat_map.keys())

        fields_ui = {}
        labels = ["Patient*", "Date* (YYYY-MM-DD)", "Time* (HH:MM)", "Reason", "Doctor", "Status", "Notes"]
        keys   = ["patient",  "date",               "time",           "reason", "doctor", "status", "notes"]
        combos = {
            "status": ["Scheduled", "Confirmed", "Completed", "Cancelled", "No-Show"],
            "patient": pat_names,
        }

        for i, (lbl, key) in enumerate(zip(labels, keys)):
            tb.Label(dlg, text=lbl).grid(row=i, column=0, padx=20, pady=5, sticky="w")
            if key in combos:
                var = tk.StringVar()
                cb = ttk.Combobox(dlg, textvariable=var, values=combos[key], width=28)
                cb.grid(row=i, column=1, padx=20, pady=5)
                fields_ui[key] = var
            else:
                e = tb.Entry(dlg, width=30)
                e.grid(row=i, column=1, padx=20, pady=5)
                fields_ui[key] = e

        if edit and record:
            # record: (ID, Patient name, date, time, reason, doctor, status)
            fields_ui["patient"].set(record[1])
            fields_ui["date"].delete(0, END); fields_ui["date"].insert(0, record[2])
            fields_ui["time"].delete(0, END); fields_ui["time"].insert(0, record[3])
            fields_ui["reason"].delete(0, END); fields_ui["reason"].insert(0, record[4] or "")
            fields_ui["doctor"].delete(0, END); fields_ui["doctor"].insert(0, record[5] or "")
            fields_ui["status"].set(record[6] or "Scheduled")

        def save():
            pat_name = fields_ui["patient"].get()
            if pat_name not in pat_map:
                messagebox.showerror("Validation", "Select a valid patient.", parent=dlg); return
            appt_date = fields_ui["date"].get().strip()
            appt_time = fields_ui["time"].get().strip()
            if not appt_date or not appt_time:
                messagebox.showerror("Validation", "Date and time are required.", parent=dlg); return
            data = {k: (v.get() if isinstance(v, tk.StringVar) else v.get()) for k, v in fields_ui.items()}
            conn = get_conn()
            if edit:
                conn.execute("""UPDATE appointments SET patient_id=?,date=?,time=?,reason=?,doctor=?,status=?,notes=?
                                WHERE id=?""",
                             (pat_map[pat_name], data["date"], data["time"], data["reason"],
                              data["doctor"], data["status"], data["notes"], record[0]))
            else:
                conn.execute("INSERT INTO appointments (patient_id,date,time,reason,doctor,status,notes) VALUES (?,?,?,?,?,?,?)",
                             (pat_map[pat_name], data["date"], data["time"], data["reason"],
                              data["doctor"], data["status"] or "Scheduled", data["notes"]))
            conn.commit()
            conn.close()
            dlg.destroy()
            self._load_appointments()

        tb.Button(dlg, text="Save", bootstyle="success", command=save).grid(row=len(labels), column=0, columnspan=2, pady=14)

    # ─────────────────────────────────────────
    # TREATMENTS
    # ─────────────────────────────────────────

    def _show_treatments(self):
        self._clear_page("Treatments")
        f = self.page_frame

        toolbar = tb.Frame(f)
        toolbar.pack(fill=X, pady=(0, 8))
        tb.Button(toolbar, text="+ Add Treatment", bootstyle="success",
                  command=self._treatment_form).pack(side=LEFT)

        cols = ("ID", "Patient", "Treatment", "Tooth #", "Cost (TZS)", "Date", "Notes")
        self.treat_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        widths = [40, 160, 180, 70, 120, 100, 200]
        for col, w in zip(cols, widths):
            self.treat_tree.heading(col, text=col)
            self.treat_tree.column(col, width=w)
        scroll = ttk.Scrollbar(f, orient=VERTICAL, command=self.treat_tree.yview)
        self.treat_tree.configure(yscrollcommand=scroll.set)
        self.treat_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=LEFT, fill=Y)
        self.treat_tree.bind("<Double-1>", lambda e: self._treatment_form(edit=True))
        self._load_treatments()

    def _load_treatments(self):
        conn = get_conn()
        rows = conn.execute("""
            SELECT t.id, p.name, t.treatment_name, t.tooth_number,
                   t.cost, t.date, t.notes
            FROM treatments t JOIN patients p ON t.patient_id=p.id
            ORDER BY t.date DESC
        """).fetchall()
        conn.close()
        self.treat_tree.delete(*self.treat_tree.get_children())
        for row in rows:
            self.treat_tree.insert("", END, values=row)

    def _treatment_form(self, edit=False):
        record = None
        if edit:
            sel = self.treat_tree.selection()
            if not sel:
                return
            record = self.treat_tree.item(sel[0])["values"]

        dlg = tb.Toplevel(self)
        dlg.title("Edit Treatment" if edit else "Add Treatment")
        dlg.geometry("420x380")
        dlg.grab_set()

        conn = get_conn()
        patients = conn.execute("SELECT id, name FROM patients ORDER BY name").fetchall()
        conn.close()
        pat_map = {p[1]: p[0] for p in patients}

        common_treatments = ["Scaling & Polishing", "Extraction", "Root Canal Treatment",
                              "Composite Filling", "Crown/Bridge", "Denture", "Whitening",
                              "Orthodontic Banding", "X-Ray", "Consultation"]

        labels = ["Patient*", "Treatment*", "Tooth #", "Cost (TZS)", "Date (YYYY-MM-DD)", "Notes"]
        keys   = ["patient",  "treatment",  "tooth",   "cost",       "date",               "notes"]
        fields_ui = {}

        for i, (lbl, key) in enumerate(zip(labels, keys)):
            tb.Label(dlg, text=lbl).grid(row=i, column=0, padx=20, pady=6, sticky="w")
            if key == "patient":
                var = tk.StringVar()
                cb = ttk.Combobox(dlg, textvariable=var, values=list(pat_map.keys()), width=28)
                cb.grid(row=i, column=1, padx=20, pady=6)
                fields_ui[key] = var
            elif key == "treatment":
                var = tk.StringVar()
                cb = ttk.Combobox(dlg, textvariable=var, values=common_treatments, width=28)
                cb.grid(row=i, column=1, padx=20, pady=6)
                fields_ui[key] = var
            else:
                e = tb.Entry(dlg, width=30)
                e.grid(row=i, column=1, padx=20, pady=6)
                fields_ui[key] = e

        if edit and record:
            fields_ui["patient"].set(record[1])
            fields_ui["treatment"].set(record[2])
            fields_ui["tooth"].delete(0,END); fields_ui["tooth"].insert(0, record[3] or "")
            fields_ui["cost"].delete(0,END);  fields_ui["cost"].insert(0, record[4] or "")
            fields_ui["date"].delete(0,END);  fields_ui["date"].insert(0, record[5] or "")
            fields_ui["notes"].delete(0,END); fields_ui["notes"].insert(0, record[6] or "")
        else:
            fields_ui["date"].insert(0, date.today().isoformat())

        def save():
            pat_name  = fields_ui["patient"].get()
            treatment = fields_ui["treatment"].get().strip() if isinstance(fields_ui["treatment"], tk.StringVar) else fields_ui["treatment"].get()
            if pat_name not in pat_map:
                messagebox.showerror("Validation", "Select a valid patient.", parent=dlg); return
            if not treatment:
                messagebox.showerror("Validation", "Treatment name is required.", parent=dlg); return
            try:
                cost = float(fields_ui["cost"].get() or 0)
            except ValueError:
                messagebox.showerror("Validation", "Cost must be a number.", parent=dlg); return

            def gv(k):
                v = fields_ui[k]
                return v.get() if isinstance(v, tk.StringVar) else v.get()

            conn = get_conn()
            if edit:
                conn.execute("""UPDATE treatments SET patient_id=?,treatment_name=?,tooth_number=?,cost=?,date=?,notes=?
                                WHERE id=?""",
                             (pat_map[pat_name], gv("treatment"), gv("tooth"), cost, gv("date"), gv("notes"), record[0]))
            else:
                conn.execute("INSERT INTO treatments (patient_id,treatment_name,tooth_number,cost,date,notes) VALUES (?,?,?,?,?,?)",
                             (pat_map[pat_name], gv("treatment"), gv("tooth"), cost, gv("date"), gv("notes")))
            conn.commit()
            conn.close()
            dlg.destroy()
            self._load_treatments()

        tb.Button(dlg, text="Save", bootstyle="success", command=save).grid(row=len(labels), column=0, columnspan=2, pady=14)

    # ─────────────────────────────────────────
    # BILLING
    # ─────────────────────────────────────────

    def _show_billing(self):
        self._clear_page("Billing")
        f = self.page_frame

        toolbar = tb.Frame(f)
        toolbar.pack(fill=X, pady=(0, 8))
        tb.Button(toolbar, text="+ New Invoice", bootstyle="success",
                  command=self._invoice_form).pack(side=LEFT, padx=(0,6))
        tb.Button(toolbar, text="💰 Record Payment", bootstyle="info",
                  command=self._record_payment).pack(side=LEFT)

        cols = ("ID", "Patient", "Date", "Total (TZS)", "Paid (TZS)", "Balance", "Status")
        self.inv_tree = ttk.Treeview(f, columns=cols, show="headings", height=20)
        widths = [40, 160, 100, 120, 120, 120, 90]
        for col, w in zip(cols, widths):
            self.inv_tree.heading(col, text=col)
            self.inv_tree.column(col, width=w)
        self.inv_tree.tag_configure("Paid",    foreground="#22c55e")
        self.inv_tree.tag_configure("Unpaid",  foreground="#ef4444")
        self.inv_tree.tag_configure("Partial", foreground="#f59e0b")
        scroll = ttk.Scrollbar(f, orient=VERTICAL, command=self.inv_tree.yview)
        self.inv_tree.configure(yscrollcommand=scroll.set)
        self.inv_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scroll.pack(side=LEFT, fill=Y)
        self._load_invoices()

    def _load_invoices(self):
        conn = get_conn()
        rows = conn.execute("""
            SELECT i.id, p.name, i.date, i.total, i.paid,
                   (i.total - i.paid) as balance, i.status
            FROM invoices i JOIN patients p ON i.patient_id=p.id
            ORDER BY i.date DESC
        """).fetchall()
        conn.close()
        self.inv_tree.delete(*self.inv_tree.get_children())
        for row in rows:
            tag = row[6] if row[6] in ("Paid","Unpaid","Partial") else ""
            formatted = (row[0], row[1], row[2],
                         f"{row[3]:,.0f}", f"{row[4]:,.0f}", f"{row[5]:,.0f}", row[6])
            self.inv_tree.insert("", END, values=formatted, tags=(tag,))

    def _invoice_form(self):
        dlg = tb.Toplevel(self)
        dlg.title("New Invoice")
        dlg.geometry("500x460")
        dlg.grab_set()

        conn = get_conn()
        patients = conn.execute("SELECT id, name FROM patients ORDER BY name").fetchall()
        conn.close()
        pat_map = {p[1]: p[0] for p in patients}

        tb.Label(dlg, text="Patient*").grid(row=0, column=0, padx=20, pady=8, sticky="w")
        pat_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=pat_var, values=list(pat_map.keys()), width=28).grid(row=0, column=1, padx=20)

        tb.Label(dlg, text="Date*").grid(row=1, column=0, padx=20, pady=8, sticky="w")
        date_e = tb.Entry(dlg, width=30); date_e.grid(row=1, column=1, padx=20)
        date_e.insert(0, date.today().isoformat())

        tb.Label(dlg, text="Notes").grid(row=2, column=0, padx=20, pady=8, sticky="w")
        notes_e = tb.Entry(dlg, width=30); notes_e.grid(row=2, column=1, padx=20)

        # Items sub-section
        tb.Label(dlg, text="Invoice Items", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, columnspan=2, pady=(12,4))

        items_frame = tb.Frame(dlg)
        items_frame.grid(row=4, column=0, columnspan=2, padx=20)

        item_rows = []
        def add_item_row(desc="", qty=1, price=0):
            r = len(item_rows)
            d = tb.Entry(items_frame, width=18); d.grid(row=r, column=0, padx=2, pady=2)
            d.insert(0, desc)
            q = tb.Entry(items_frame, width=6);  q.grid(row=r, column=1, padx=2, pady=2)
            q.insert(0, str(qty))
            p = tb.Entry(items_frame, width=10); p.grid(row=r, column=2, padx=2, pady=2)
            p.insert(0, str(price))
            item_rows.append((d, q, p))

        for hdr, col in [("Description",0),("Qty",1),("Unit Price",2)]:
            tb.Label(items_frame, text=hdr, font=("Segoe UI",8,"bold")).grid(row=0, column=col, padx=2)
        # pre-add 3 rows
        add_item_row()
        add_item_row()
        add_item_row()

        tb.Button(dlg, text="+ Add Row", bootstyle="secondary",
                  command=add_item_row).grid(row=5, column=0, columnspan=2, pady=4)

        def save():
            if pat_var.get() not in pat_map:
                messagebox.showerror("Validation", "Select a valid patient.", parent=dlg); return
            total = 0.0
            items = []
            for d_e, q_e, p_e in item_rows:
                desc = d_e.get().strip()
                if not desc:
                    continue
                try:
                    qty = int(q_e.get() or 1)
                    price = float(p_e.get() or 0)
                except ValueError:
                    messagebox.showerror("Validation","Qty and price must be numbers.",parent=dlg); return
                total += qty * price
                items.append((desc, qty, price))
            conn = get_conn()
            c = conn.cursor()
            c.execute("INSERT INTO invoices (patient_id,date,total,paid,status,notes) VALUES (?,?,?,0,'Unpaid',?)",
                      (pat_map[pat_var.get()], date_e.get(), total, notes_e.get()))
            inv_id = c.lastrowid
            for desc, qty, price in items:
                c.execute("INSERT INTO invoice_items (invoice_id,description,quantity,unit_price) VALUES (?,?,?,?)",
                          (inv_id, desc, qty, price))
            conn.commit()
            conn.close()
            dlg.destroy()
            self._load_invoices()

        tb.Button(dlg, text="Save Invoice", bootstyle="success", command=save).grid(row=6, column=0, columnspan=2, pady=12)

    def _record_payment(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo("Select Invoice", "Please select an invoice first.")
            return
        record = self.inv_tree.item(sel[0])["values"]
        inv_id = record[0]
        balance = float(str(record[5]).replace(",",""))

        amount = simpledialog.askfloat("Record Payment",
            f"Invoice #{inv_id}\nBalance: TZS {balance:,.0f}\n\nEnter payment amount:",
            parent=self, minvalue=0)
        if amount is None:
            return
        conn = get_conn()
        row = conn.execute("SELECT total, paid FROM invoices WHERE id=?", (inv_id,)).fetchone()
        new_paid = row[1] + amount
        status = "Paid" if new_paid >= row[0] else "Partial"
        conn.execute("UPDATE invoices SET paid=?, status=? WHERE id=?", (new_paid, status, inv_id))
        conn.commit()
        conn.close()
        self._load_invoices()
        messagebox.showinfo("Payment Recorded", f"TZS {amount:,.0f} recorded.\nStatus: {status}")

    # ─────────────────────────────────────────
    # UTILITY
    # ─────────────────────────────────────────

    def _sort_tree(self, tree, col):
        data = [(tree.set(child, col), child) for child in tree.get_children("")]
        data.sort()
        for i, (_, child) in enumerate(data):
            tree.move(child, "", i)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app = DentalApp()
    app.mainloop()
