import csv
import os 
from Constants import *
from helper_functions import *
from tkinter import ttk, messagebox, filedialog

class DashboardWindow:
    def __init__(self, root, user):
        self.root  = root
        self.user  = user
        self.role  = user["role"].lower()
        self.is_admin = self.role == "admin"
        self.emp_list  = []
        self._all_rows = []     # master cache for live filtering
        self._sort_col = None   # "Name" | "Department" | "Salary"
        self._sort_asc = True
        self._live_after = None # pending after() id for debounce

        root.title("Employee Management System")
        root.configure(bg=BG)
        root.resizable(True, True)
        center(root, 980, 820)
        self._build()
        root.mainloop()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=PRIMARY, height=48)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="Employee Management System",
                 font=F(13, bold=True), bg=PRIMARY, fg="#fff").pack(
                     side="left", padx=20, pady=12)

        # Right side of topbar: role badge + logout
        right = tk.Frame(topbar, bg=PRIMARY)
        right.pack(side="right", padx=16)

        rs = ROLE_STYLE.get(self.role, ROLE_STYLE["user"])
        tk.Label(right, text=f"  {self.user['username']}  ",
                 font=F(10), bg=PRIMARY, fg="#dbeafe").pack(side="left", padx=(0, 6))
        tk.Label(right, text=f"  {rs['label']}  ",
                 font=F(9, bold=True), bg=rs["bg"], fg=rs["fg"],
                 padx=4, pady=2).pack(side="left", padx=(0, 14))

        lo_btn = tk.Button(right, text="Log Out",
                           command=self._logout,
                           bg="#1e3a8a", fg="#fff", relief="flat",
                           activebackground="#1e40af", activeforeground="#fff",
                           cursor="hand2", font=F(9, bold=True), bd=0)
        lo_btn.pack(side="left", ipadx=10, ipady=4)

        # ── Main area ─────────────────────────────────────────────────────────
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=20, pady=16)

        # Left panel – form
        left = tk.Frame(main, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER, width=340)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)
        self._build_form(left)

        # Right column – wraps table + optional stats panel
        right_col = tk.Frame(main, bg=BG)
        right_col.pack(side="left", fill="both", expand=True)

        # Right panel – table
        right_panel = tk.Frame(right_col, bg=CARD, highlightthickness=1,
                               highlightbackground=BORDER)
        right_panel.pack(fill="both", expand=True)
        self._build_table(right_panel)

        # ── Stats panel (admin only) ──────────────────────────────────────────
        if self.is_admin:
            self._build_stats(right_col)

    def _build_form(self, parent):
        inner = tk.Frame(parent, bg=CARD)
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(inner, text="Employee Details", font=F(12, bold=True),
                 bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 14))

        # Form grid
        form = tk.Frame(inner, bg=CARD)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        # ── Search fields (all roles can use every filter) ────────────────────
        search_fields = [
            ("Employee ID", "v_id"),
            ("Name",        "v_name"),
            ("Department",  "v_dept"),
            ("Gender",      "v_gender"),
        ]
        self.vars = {}
        self.entries = {}
        for i, (lbl, key) in enumerate(search_fields):
            self.vars[key] = tk.StringVar()
            tk.Label(form, text=lbl, font=F(9, bold=True),
                     bg=CARD, fg=SUBTLE).grid(row=i, column=0, sticky="w",
                                              padx=(0, 10), pady=5)
            e = tk.Entry(form, textvariable=self.vars[key], width=22)
            style_entry(e)
            e.grid(row=i, column=1, sticky="ew", ipady=5, pady=5)
            self.entries[key] = e

        # ── Live filtering on Name and Department ─────────────────────────────
        for live_key in ("v_name", "v_dept"):
            self.vars[live_key].trace_add(
                "write", lambda *_, k=live_key: self._on_live_filter()
            )

        # Salary range row — two inputs side by side
        row_sal = len(search_fields)
        self.vars["v_sal_min"] = tk.StringVar()
        self.vars["v_sal_max"] = tk.StringVar()

        tk.Label(form, text="Salary Range", font=F(9, bold=True),
                 bg=CARD, fg=SUBTLE).grid(row=row_sal, column=0, sticky="w",
                                          padx=(0, 10), pady=5)
        sal_frame = tk.Frame(form, bg=CARD)
        sal_frame.grid(row=row_sal, column=1, sticky="ew", pady=5)
        sal_frame.columnconfigure(0, weight=1)
        sal_frame.columnconfigure(2, weight=1)

        e_min = tk.Entry(sal_frame, textvariable=self.vars["v_sal_min"], width=9)
        style_entry(e_min)
        e_min.grid(row=0, column=0, sticky="ew", ipady=5)
        tk.Label(sal_frame, text="to", font=F(9), bg=CARD, fg=SUBTLE).grid(
            row=0, column=1, padx=5)
        e_max = tk.Entry(sal_frame, textvariable=self.vars["v_sal_max"], width=9)
        style_entry(e_max)
        e_max.grid(row=0, column=2, sticky="ew", ipady=5)
        self.entries["v_sal_min"] = e_min
        self.entries["v_sal_max"] = e_max

        # Thin divider before CRUD-only fields
        tk.Frame(form, bg=BORDER, height=1).grid(
            row=row_sal + 1, column=0, columnspan=2, sticky="ew", pady=8)

        # ── CRUD-only fields (used by admin Insert/Update; read-only display) ─
        crud_fields = [
            ("Salary",  "v_salary"),
            ("Contact", "v_contact"),
        ]
        for j, (lbl, key) in enumerate(crud_fields):
            self.vars[key] = tk.StringVar()
            lbl_w = tk.Label(form, text=lbl, font=F(9, bold=True),
                             bg=CARD, fg=SUBTLE if self.is_admin else "#c0c0c0")
            lbl_w.grid(row=row_sal + 2 + j, column=0, sticky="w",
                       padx=(0, 10), pady=5)
            e = tk.Entry(form, textvariable=self.vars[key], width=22)
            style_entry(e)
            e.grid(row=row_sal + 2 + j, column=1, sticky="ew", ipady=5, pady=5)
            self.entries[key] = e
            if not self.is_admin:
                e.configure(state="disabled", bg="#f9f9f9", fg=SUBTLE)

        # Divider
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=14)

        # ── Buttons ───────────────────────────────────────────────────────────
        # Search + Clear — always active for all roles
        search_row = tk.Frame(inner, bg=CARD)
        search_row.pack(fill="x", pady=(0, 6))

        srch = tk.Button(search_row, text="Search", command=self._search)
        style_btn(srch)
        srch.pack(side="left", ipadx=10, ipady=6, expand=True, fill="x", padx=(0, 6))

        clr = tk.Button(search_row, text="Clear Form", command=self._clear_form)
        style_btn(clr, primary=False)
        clr.pack(side="left", ipadx=6, ipady=6, expand=True, fill="x")

        # Show All button — always active for all roles
        all_row = tk.Frame(inner, bg=CARD)
        all_row.pack(fill="x", pady=(0, 6))

        all_btn = tk.Button(all_row, text="Show All Employees", command=self._show_all)
        style_btn(all_btn)
        all_btn.pack(side="left", ipadx=10, ipady=6, expand=True, fill="x")

        # CRUD buttons — shown for all roles; greyed/disabled for non-admin
        crud_row1 = tk.Frame(inner, bg=CARD)
        crud_row1.pack(fill="x", pady=(0, 6))

        ins = tk.Button(crud_row1, text="Insert", command=self._insert)
        upd = tk.Button(crud_row1, text="Update", command=self._update)
        if self.is_admin:
            style_btn(ins)
            style_btn(upd, primary=False)
        else:
            for b in (ins, upd):
                b.configure(bg="#e5e7eb", fg="#9ca3af", relief="flat", bd=0,
                            font=F(10, bold=True), state="disabled", cursor="arrow")
        ins.pack(side="left", ipadx=10, ipady=6, expand=True, fill="x", padx=(0, 6))
        upd.pack(side="left", ipadx=10, ipady=6, expand=True, fill="x")

        crud_row2 = tk.Frame(inner, bg=CARD)
        crud_row2.pack(fill="x", pady=(0, 6))

        dlt = tk.Button(crud_row2, text="Delete", command=self._delete)
        rst = tk.Button(crud_row2, text="Reset All", command=self._reset)
        if self.is_admin:
            style_btn(dlt, danger=True)
            style_btn(rst, primary=False)
        else:
            for b in (dlt, rst):
                b.configure(bg="#e5e7eb", fg="#9ca3af", relief="flat", bd=0,
                            font=F(10, bold=True), state="disabled", cursor="arrow")
        dlt.pack(side="left", ipadx=10, ipady=6, expand=True, fill="x", padx=(0, 6))
        rst.pack(side="left", ipadx=6, ipady=6, expand=True, fill="x")

        # Export button — available to ALL roles
        exp_row = tk.Frame(inner, bg=CARD)
        exp_row.pack(fill="x", pady=(0, 6))

        exp = tk.Button(exp_row, text="Export Results", command=self._export_dialog)
        if self.is_admin:
            style_btn(exp)
        else:
            exp.configure(bg="#e5e7eb", fg="#9ca3af", relief="flat", bd=0,
                          font=F(10, bold=True), state="disabled", cursor="arrow")
        exp.pack(side="left", ipadx=10, ipady=6, expand=True, fill="x")

        # Status
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=14)
        self.status = tk.Label(inner, text="", font=F(9),
                               bg=CARD, fg=OK, wraplength=280, justify="left")
        self.status.pack(anchor="w")

    # ── Statistics Panel (admin-only) ────────────────────────────────────────

    def _build_stats(self, parent):
        """Build the collapsible Statistics panel below the Treeview."""
        STAT_BG    = "#f8fafc"
        STAT_CARD  = "#ffffff"

        # ── Outer container ──────────────────────────────────────────────────
        self.stats_frame = tk.Frame(parent, bg=STAT_BG,
                                    highlightthickness=1,
                                    highlightbackground=BORDER)
        self.stats_frame.pack(fill="x", pady=(10, 0))

        # ── Header bar ───────────────────────────────────────────────────────
        hdr = tk.Frame(self.stats_frame, bg=BORDER)
        hdr.pack(fill="x")

        tk.Label(hdr, text="Statistics",
                 font=F(10, bold=True), bg=BORDER, fg=TEXT,
                 pady=7, padx=12).pack(side="left")

        self._stats_collapsed = False
        self._toggle_btn = tk.Button(
            hdr, text="Collapse",
            command=self._toggle_stats,
            bg=BORDER, fg=SUBTLE, relief="flat", bd=0,
            activebackground="#d1d5db", activeforeground=TEXT,
            cursor="hand2", font=F(9))
        self._toggle_btn.pack(side="right", padx=12)

        refresh_btn = tk.Button(
            hdr, text="Refresh",
            command=self._refresh_stats,
            bg=BORDER, fg=SUBTLE, relief="flat", bd=0,
            activebackground="#d1d5db", activeforeground=TEXT,
            cursor="hand2", font=F(9))
        refresh_btn.pack(side="right", padx=(0, 4), ipadx=6, ipady=2)

        # ── Collapsible body ─────────────────────────────────────────────────
        self._stats_body = tk.Frame(self.stats_frame, bg=STAT_BG)
        self._stats_body.pack(fill="x", padx=12, pady=10)

        # ── Row 1 – Salary KPI cards ─────────────────────────────────────────
        kpi_row = tk.Frame(self._stats_body, bg=STAT_BG)
        kpi_row.pack(fill="x")

        kpi_defs = [
            ("Highest Salary",       "stat_highest"),
            ("Lowest Salary",        "stat_lowest"),
            ("Average Salary",       "stat_average"),
            ("Total Salary Expense", "stat_total"),
        ]

        for i, (title, attr) in enumerate(kpi_defs):
            card = tk.Frame(kpi_row, bg=STAT_CARD, highlightthickness=1,
                            highlightbackground=BORDER)
            card.grid(row=0, column=i, sticky="nsew", padx=(0, 8) if i < 3 else (0, 0))
            kpi_row.columnconfigure(i, weight=1)

            tk.Label(card, text=title,
                     font=F(8, bold=True), bg=STAT_CARD, fg=SUBTLE,
                     pady=6, padx=10, anchor="w").pack(fill="x")

            val_lbl = tk.Label(card, text="—",
                               font=F(14, bold=True), bg=STAT_CARD, fg=TEXT,
                               padx=10, anchor="w")
            val_lbl.pack(fill="x", pady=(0, 8))
            setattr(self, attr, val_lbl)

        # ── Row 2 – Department-wise count ─────────────────────────────────────
        tk.Frame(self._stats_body, bg=BORDER, height=1).pack(fill="x", pady=(10, 8))

        dept_hdr = tk.Frame(self._stats_body, bg=STAT_BG)
        dept_hdr.pack(fill="x", pady=(0, 6))
        tk.Label(dept_hdr, text="Department-wise Employee Count",
                 font=F(10, bold=True), bg=STAT_BG, fg=TEXT).pack(side="left")

        # Treeview for dept counts
        dept_cols = ("Department", "Employees")
        dept_style = ttk.Style()
        dept_style.configure("Dept.Treeview",
                             background=STAT_CARD, foreground=TEXT,
                             fieldbackground=STAT_CARD, rowheight=24,
                             font=("Helvetica", 9))
        dept_style.configure("Dept.Treeview.Heading",
                             background="#e2e8f0", foreground=TEXT,
                             font=("Helvetica", 9, "bold"), relief="flat")
        dept_style.map("Dept.Treeview",
                       background=[("selected", "#dbeafe")],
                       foreground=[("selected", "#1e3a8a")])

        dept_frame = tk.Frame(self._stats_body, bg=STAT_BG)
        dept_frame.pack(fill="x")

        self.dept_tree = ttk.Treeview(dept_frame, columns=dept_cols,
                                      show="headings", style="Dept.Treeview",
                                      height=5)
        self.dept_tree.heading("Department", text="Department")
        self.dept_tree.heading("Employees",  text="No. of Employees")
        self.dept_tree.column("Department", width=220, stretch=True)
        self.dept_tree.column("Employees",  width=120, anchor="center", stretch=False)

        dept_vsb = ttk.Scrollbar(dept_frame, orient="vertical",
                                  command=self.dept_tree.yview)
        self.dept_tree.configure(yscrollcommand=dept_vsb.set)
        self.dept_tree.grid(row=0, column=0, sticky="nsew")
        dept_vsb.grid(row=0, column=1, sticky="ns")
        dept_frame.columnconfigure(0, weight=1)

        # Alternate row colors
        self.dept_tree.tag_configure("odd",  background="#f8fafc")
        self.dept_tree.tag_configure("even", background=STAT_CARD)

        # Load data immediately
        self._refresh_stats()

    def _toggle_stats(self):
        if self._stats_collapsed:
            self._stats_body.pack(fill="x", padx=12, pady=10)
            self._toggle_btn.config(text="Collapse")
            self._stats_collapsed = False
        else:
            self._stats_body.pack_forget()
            self._toggle_btn.config(text="Expand")
            self._stats_collapsed = True

    def _refresh_stats(self, rows=None):
        """Update stat widgets.

        If *rows* is provided (a list of EMPLOYEES tuples already fetched),
        stats are computed from that subset in-memory — no extra DB call.
        Without rows the full-table DB query is used (initial load).

        Row tuple layout: (EMPID, NAME, GENDER, DEPARTMENT, SALARY, CONTACT)
        """
        if rows is not None:
            # ── Compute from the supplied subset ─────────────────────────────
            salaries = []
            for r in rows:
                try:
                    if r[4] is not None:
                        salaries.append(float(r[4]))
                except (TypeError, ValueError):
                    pass

            if salaries:
                highest = max(salaries)
                lowest  = min(salaries)
                average = sum(salaries) / len(salaries)
                total   = sum(salaries)
            else:
                highest = lowest = average = total = 0

            dept_map = {}
            for r in rows:
                dept = r[3] or "—"
                dept_map[dept] = dept_map.get(dept, 0) + 1
            dept_counts = sorted(dept_map.items(), key=lambda x: x[1], reverse=True)

            stats = {
                "highest": highest, "lowest": lowest,
                "average": average, "total": total,
                "dept_counts": dept_counts,
            }
        else:
            # ── Fall back to full DB query ────────────────────────────────────
            try:
                stats = db_get_stats()
            except Exception as e:
                messagebox.showerror("Statistics Error",
                                     f"Could not load statistics:\n{e}",
                                     parent=self.root)
                return

        fmt = lambda v: f"PKR {v:,.0f}"
        self.stat_highest.config(text=fmt(stats["highest"]))
        self.stat_lowest.config( text=fmt(stats["lowest"]))
        self.stat_average.config(text=fmt(stats["average"]))
        self.stat_total.config(  text=fmt(stats["total"]))

        for item in self.dept_tree.get_children():
            self.dept_tree.delete(item)

        for idx, (dept, cnt) in enumerate(stats["dept_counts"]):
            tag = "odd" if idx % 2 == 0 else "even"
            self.dept_tree.insert("", "end",
                                  values=(dept or "—", cnt),
                                  tags=(tag,))

        if not stats["dept_counts"]:
            self.dept_tree.insert("", "end",
                                  values=("No data", "—"))

    def _build_table(self, parent):
        inner = tk.Frame(parent, bg=CARD)
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(inner, text="Employee Records", font=F(12, bold=True),
                 bg=CARD, fg=TEXT).pack(anchor="w", pady=(0, 10))

        # Treeview
        cols = ("ID", "Name", "Gender", "Department", "Salary", "Contact")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background=CARD, foreground=TEXT,
                        fieldbackground=CARD, rowheight=28,
                        font=("Helvetica", 10))
        style.configure("Custom.Treeview.Heading",
                        background="#f1f5f9", foreground=TEXT,
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Custom.Treeview",
                  background=[("selected", "#dbeafe")],
                  foreground=[("selected", "#1e3a8a")])

        frame_tree = tk.Frame(inner, bg=CARD)
        frame_tree.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(frame_tree, columns=cols,
                                 show="headings", style="Custom.Treeview")
        widths = {"ID": 70, "Name": 140, "Gender": 70,
                  "Department": 130, "Salary": 90, "Contact": 110}
        # Map sortable column names to their index in the row tuple
        self._sort_col_index = {"Name": 1, "Department": 3, "Salary": 4}

        for col in cols:
            if col in self._sort_col_index:
                self.tree.heading(col, text=col,
                                  command=lambda c=col: self._sort_by(c))
            else:
                self.tree.heading(col, text=col)
            self.tree.column(col, width=widths[col], minwidth=60, stretch=True)

        vsb = ttk.Scrollbar(frame_tree, orient="vertical",
                             command=self.tree.yview)
        hsb = ttk.Scrollbar(frame_tree, orient="horizontal",
                             command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame_tree.rowconfigure(0, weight=1)
        frame_tree.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Bottom row: record count
        bot = tk.Frame(inner, bg=CARD)
        bot.pack(fill="x", pady=(8, 0))
        self.count_label = tk.Label(bot, text="No records loaded.",
                                    font=F(9), bg=CARD, fg=SUBTLE)
        self.count_label.pack(side="left")

    # ── Treeview helpers ──────────────────────────────────────────────────────

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        row = self.emp_list[idx]
        # DB column order: EMPID, NAME, GENDER, DEPARTMENT, SALARY, CONTACT
        mapping = [("v_id",0),("v_name",1),("v_gender",2),("v_dept",3),("v_salary",4),("v_contact",5)]
        for key, col in mapping:
            self.vars[key].set(row[col] if row[col] is not None else "")
        # Clear salary range fields on row select (they are search-only)
        self.vars["v_sal_min"].set("")
        self.vars["v_sal_max"].set("")

    def _update_table(self, rows, *, update_cache=True):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.emp_list  = list(rows)
        if update_cache:
            self._all_rows = list(self.emp_list)
        self._sort_col = None
        self._sort_asc = True
        self._reset_heading_arrows()
        for idx, r in enumerate(self.emp_list):
            self.tree.insert("", "end", iid=str(idx),
                             values=(r[0], r[1], r[2], r[3], r[4], r[5]))
        n = len(self.emp_list)
        self.count_label.config(text=f"{n} record{'s' if n != 1 else ''} found.")

    def _reset_heading_arrows(self):
        """Remove ▲/▼ from all sortable column headings."""
        for col in self._sort_col_index:
            self.tree.heading(col, text=col)

    def _sort_by(self, col):
        """Toggle sort direction if same column, else sort ascending on new column."""
        if not self.emp_list:
            return
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self._apply_sort()

    def _apply_sort(self):
        """Sort self.emp_list by the active column and repopulate the treeview."""
        if self._sort_col is None:
            return
        idx = self._sort_col_index[self._sort_col]

        def sort_key(row):
            val = row[idx]
            if val is None:
                # None sorts last regardless of direction
                return (1, 0) if self._sort_col == "Salary" else (1, "")
            if self._sort_col == "Salary":
                try:
                    return (0, float(val))
                except (ValueError, TypeError):
                    return (0, 0.0)
            return (0, str(val).lower())

        self.emp_list.sort(key=sort_key, reverse=not self._sort_asc)

        # Repopulate treeview preserving selection
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, r in enumerate(self.emp_list):
            self.tree.insert("", "end", iid=str(i),
                             values=(r[0], r[1], r[2], r[3], r[4], r[5]))

        # Update heading arrows: active col gets arrow, others plain
        arrow = " ▲" if self._sort_asc else " ▼"
        for col in self._sort_col_index:
            label = col + (arrow if col == self._sort_col else "")
            self.tree.heading(col, text=label)

        n = len(self.emp_list)
        self.count_label.config(text=f"{n} record{'s' if n != 1 else ''} found.")

    def _on_live_filter(self):
        """Debounce: wait 150 ms after the last keystroke before filtering."""
        if self._live_after is not None:
            self.root.after_cancel(self._live_after)
        self._live_after = self.root.after(150, self._apply_live_filter)

    def _apply_live_filter(self):
        """Filter _all_rows client-side by current Name and Department values."""
        self._live_after = None
        if not self._all_rows:
            return  # nothing loaded yet — nothing to filter

        name_q = self.vars["v_name"].get().strip().lower()
        dept_q = self.vars["v_dept"].get().strip().lower()

        if not name_q and not dept_q:
            filtered = self._all_rows
        else:
            filtered = [
                r for r in self._all_rows
                if (not name_q or (r[1] and name_q in str(r[1]).lower()))
                and (not dept_q or (r[3] and dept_q in str(r[3]).lower()))
            ]

        # Repopulate the treeview without touching _all_rows
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.emp_list = list(filtered)
        for idx, r in enumerate(self.emp_list):
            self.tree.insert("", "end", iid=str(idx),
                             values=(r[0], r[1], r[2], r[3], r[4], r[5]))
        n = len(self.emp_list)
        if n == len(self._all_rows):
            self.count_label.config(
                text=f"{n} record{'s' if n != 1 else ''} found.")
        else:
            self.count_label.config(
                text=f"{n} of {len(self._all_rows)} record"
                     f"{'s' if len(self._all_rows) != 1 else ''} shown.")

    def _set_status(self, msg, color=OK):
        self.status.config(text=msg, fg=color)

    # ── Form helpers ──────────────────────────────────────────────────────────

    def _show_all(self):
        """Fetch and display every employee record, clearing all filters first."""
        for v in self.vars.values():
            v.set("")
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM EMPLOYEES ORDER BY EMPID")
                    rows = cur.fetchall()
            if rows:
                self._update_table(rows)
                self._set_status(f"Showing all {len(rows)} employee record(s).")
                if self.is_admin:
                    self._refresh_stats(rows)
            else:
                self._set_status("No employee records found in the database.", ERR)
        except Exception as e:
            self._set_status(f"Error: {e}", ERR)

    def _reload_table(self):
        """Silently refresh the treeview with all current DB records."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM EMPLOYEES ORDER BY EMPID")
                    rows = cur.fetchall()
            self._update_table(rows)
            if self.is_admin:
                self._refresh_stats(rows)
        except Exception as e:
            self._set_status(f"Refresh error: {e}", ERR)

    def _clear_form(self):
        for v in self.vars.values():
            v.set("")
        self._set_status("")

    def _reset(self):
        self._clear_form()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.emp_list  = []
        self._all_rows = []
        self.count_label.config(text="No records loaded.")

    # ── CRUD Operations ───────────────────────────────────────────────────────

    def _search(self):
        empid   = self.vars["v_id"].get().strip()
        name    = self.vars["v_name"].get().strip()
        dept    = self.vars["v_dept"].get().strip()
        gender  = self.vars["v_gender"].get().strip()
        sal_min = self.vars["v_sal_min"].get().strip()
        sal_max = self.vars["v_sal_max"].get().strip()

        # ── Validate salary range inputs ──────────────────────────────────────
        sal_min_val = sal_max_val = None
        if sal_min:
            try:
                sal_min_val = float(sal_min)
            except ValueError:
                self._set_status("Salary Min must be a number.", ERR); return
        if sal_max:
            try:
                sal_max_val = float(sal_max)
            except ValueError:
                self._set_status("Salary Max must be a number.", ERR); return
        if sal_min_val is not None and sal_max_val is not None:
            if sal_min_val > sal_max_val:
                self._set_status("Salary Min cannot exceed Salary Max.", ERR); return
            
            if sal_min_val < 0 or sal_max_val < 0:
                self._set_status("Salaries cannot be negative.", ERR); return

        # ── Build parameterised query ─────────────────────────────────────────
        # Rule: if Employee ID is provided it overrides all other filters.
        clauses = []
        params  = {}

        if empid:
            clauses.append("UPPER(EMPID) = UPPER(:empid)")
            params["empid"] = empid
        else:
            if name:
                clauses.append("UPPER(NAME) LIKE UPPER(:name)")
                params["name"] = f"%{name}%"
            if dept:
                clauses.append("UPPER(DEPARTMENT) LIKE UPPER(:dept)")
                params["dept"] = f"%{dept}%"
            if gender:
                clauses.append("UPPER(GENDER) = UPPER(:gender)")
                params["gender"] = gender
            if sal_min_val is not None:
                clauses.append("SALARY >= :sal_min")
                params["sal_min"] = sal_min_val
            if sal_max_val is not None:
                clauses.append("SALARY <= :sal_max")
                params["sal_max"] = sal_max_val

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        query = f"SELECT * FROM EMPLOYEES {where}"

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    rows = cur.fetchall()
            if rows:
                self._update_table(rows)
                active = []
                if empid:            active.append(f"ID='{empid}'")
                else:
                    if name:         active.append(f"Name≈'{name}'")
                    if dept:         active.append(f"Dept≈'{dept}'")
                    if gender:       active.append(f"Gender='{gender}'")
                    if sal_min_val is not None or sal_max_val is not None:
                        lo = f"{sal_min_val:,.0f}" if sal_min_val is not None else "0"
                        hi = f"{sal_max_val:,.0f}" if sal_max_val is not None else "∞"
                        active.append(f"Salary {lo}–{hi}")
                tag = ("  ·  ".join(active)) if active else "all records"
                self._set_status(f"{len(rows)} result(s) — {tag}")
                if self.is_admin:
                    self._refresh_stats(rows)
            else:
                self._set_status("No employees match the given filters.", ERR)
        except Exception as e:
            self._set_status(f"Error: {e}", ERR)

    def _insert(self):
        vals = [self.vars[k].get().strip()
                for k in ["v_id", "v_name", "v_gender", "v_dept", "v_salary", "v_contact"]]
        if not vals[0] or not vals[1]:
            self._set_status("Employee ID and Name are required.", ERR); return
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO EMPLOYEES VALUES (:1,:2,:3,:4,:5,:6)", vals)
                conn.commit()
            self._clear_form()
            self._reload_table()
            self._set_status("Employee inserted successfully.")
        except oracledb.IntegrityError:
            self._set_status("Employee ID already exists.", ERR)
        except Exception as e:
            self._set_status(f"Error: {e}", ERR)

    def _update(self):
        empid = self.vars["v_id"].get().strip()
        if not empid:
            self._set_status("Enter Employee ID to update.", ERR); return
        vals = [self.vars[k].get().strip()
                for k in ["v_name", "v_gender", "v_dept", "v_salary", "v_contact"]]
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # ── Fetch existing record to detect changes ───────────────
                    cur.execute(
                        "SELECT NAME, GENDER, DEPARTMENT, SALARY, CONTACT "
                        "FROM EMPLOYEES WHERE UPPER(EMPID) = UPPER(:1)",
                        [empid],
                    )
                    existing = cur.fetchone()
                    if existing is None:
                        self._set_status("No employee found with that ID.", ERR)
                        return

                    # Normalise DB values to strings for comparison
                    existing_vals = [
                        str(v).strip() if v is not None else "" for v in existing
                    ]
                    if existing_vals == vals:
                        self._set_status("No changes detected.", SUBTLE)
                        return

                    cur.execute("""
                        UPDATE EMPLOYEES
                        SET NAME=:1, GENDER=:2, DEPARTMENT=:3,
                            SALARY=:4, CONTACT=:5
                        WHERE EMPID=:6
                    """, vals + [empid])
                conn.commit()
            self._reload_table()
            self._set_status("Employee updated successfully.")
        except Exception as e:
            self._set_status(f"Error: {e}", ERR)

    def _delete(self):
        empid = self.vars["v_id"].get().strip()
        if not empid:
            self._set_status("Enter Employee ID to delete.", ERR); return
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete employee '{empid}'?",
                                   parent=self.root):
            return
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM EMPLOYEES WHERE EMPID=:1", [empid])
                    if cur.rowcount == 0:
                        self._set_status("No employee found with that ID.", ERR)
                        return
                conn.commit()
            self._clear_form()
            self._reload_table()
            self._set_status("Employee deleted successfully.")
        except Exception as e:
            self._set_status(f"Error: {e}", ERR)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_dialog(self):
        """Show a modal dialog to choose CSV or TXT export format."""
        if not self.emp_list:
            messagebox.showwarning("Nothing to Export",
                                   "No records are loaded in the table.\n"
                                   "Please run a Search first.",
                                   parent=self.root)
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Export Results")
        dlg.configure(bg=CARD)
        dlg.resizable(False, False)
        dlg.grab_set()
        # centre over parent
        self.root.update_idletasks()
        px = self.root.winfo_x() + self.root.winfo_width()  // 2
        py = self.root.winfo_y() + self.root.winfo_height() // 2
        dlg.geometry(f"320x210+{px - 160}+{py - 105}")

        tk.Label(dlg, text="Export Results",
                 font=F(13, bold=True), bg=CARD, fg=TEXT).pack(pady=(24, 4))
        tk.Label(dlg, text="Choose the format to save the current records:",
                 font=F(9), bg=CARD, fg=SUBTLE, wraplength=280).pack(pady=(0, 16))

        btn_frame = tk.Frame(dlg, bg=CARD)
        btn_frame.pack(padx=28, fill="x")

        def do_export(fmt):
            dlg.destroy()
            self._export_data(fmt)

        csv_btn = tk.Button(btn_frame, text="Export as CSV",
                            command=lambda: do_export("csv"))
        csv_btn.configure(bg="#e5e7eb", fg=TEXT, relief="flat", bd=0,
                          activebackground="#d1d5db", activeforeground=TEXT,
                          cursor="hand2", font=F(10, bold=True))
        csv_btn.pack(fill="x", ipady=8, pady=(0, 8))

        txt_btn = tk.Button(btn_frame, text="Export as TXT",
                            command=lambda: do_export("txt"))
        txt_btn.configure(bg="#e5e7eb", fg=TEXT, relief="flat", bd=0,
                          activebackground="#d1d5db", activeforeground=TEXT,
                          cursor="hand2", font=F(10, bold=True))
        txt_btn.pack(fill="x", ipady=8)

        tk.Button(dlg, text="Cancel", command=dlg.destroy,
                  bg=CARD, fg=SUBTLE, relief="flat", bd=0,
                  cursor="hand2", font=F(9)).pack(pady=(10, 0))

    def _export_data(self, fmt):
        """Write self.emp_list to a CSV or TXT file chosen by the user."""
        headers = ["EmpID", "Name", "Gender", "Department", "Salary", "Contact"]

        if fmt == "csv":
            filepath = filedialog.asksaveasfilename(
                parent=self.root,
                title="Save as CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="employees_export.csv",
            )
            if not filepath:
                return
            try:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    for row in self.emp_list:
                        writer.writerow([v if v is not None else "" for v in row])
                count = len(self.emp_list)
                self._set_status(f"Exported {count} record(s) to CSV successfully.")
                if messagebox.askyesno("Export Complete",
                                       f"Exported {count} record(s).\n\n"
                                       f"Open the file now?\n{filepath}",
                                       parent=self.root):
                    os.startfile(filepath)
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not write file:\n{e}",
                                     parent=self.root)

        elif fmt == "txt":
            filepath = filedialog.asksaveasfilename(
                parent=self.root,
                title="Save as TXT",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialfile="employees_export.txt",
            )
            if not filepath:
                return
            try:
                lines = []
                lines.append(", ".join(headers))
                for row in self.emp_list:
                    lines.append(", ".join(str(v) if v is not None else "" for v in row))

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))

                count = len(self.emp_list)
                self._set_status(f"Exported {count} record(s) to TXT successfully.")
                if messagebox.askyesno("Export Complete",
                                       f"Exported {count} record(s).\n\n"
                                       f"Open the file now?\n{filepath}",
                                       parent=self.root):
                    os.startfile(filepath)
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not write file:\n{e}",
                                     parent=self.root)


    def _logout(self):
        from Login import LoginWindow
        
        self.root.destroy()
        root = tk.Tk()
        LoginWindow(root)
        root.mainloop()