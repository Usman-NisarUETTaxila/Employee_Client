import oracledb
from Constants import *
import tkinter as tk
import tkinter.font as tkFont

def get_connection():
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)

def db_login(username, password):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ID, USERNAME, ROLE FROM USERS "
                "WHERE USERNAME = :u AND PASSWORD = :p",
                {"u": username, "p": password},
            )
            row = cur.fetchone()
    if row:
        return {"id": row[0], "username": row[1], "role": row[2]}
    return None

def db_register(username, password, role):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO USERS (USERNAME, PASSWORD, ROLE) VALUES (:u, :p, :r)",
                    {"u": username, "p": password, "r": role},
                )
            conn.commit()
        return True, ""
    except oracledb.IntegrityError:
        return False, "Username already taken."
    except Exception as e:
        return False, f"Database error: {e}"

def db_get_stats():
    """Return salary stats and department-wise employee counts."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    MAX(SALARY)  AS highest,
                    MIN(SALARY)  AS lowest,
                    AVG(SALARY)  AS average,
                    SUM(SALARY)  AS total
                FROM EMPLOYEES
            """)
            row = cur.fetchone()
            highest = row[0] or 0
            lowest  = row[1] or 0
            average = row[2] or 0
            total   = row[3] or 0

            cur.execute("""
                SELECT DEPARTMENT, COUNT(*) AS cnt
                FROM EMPLOYEES
                GROUP BY DEPARTMENT
                ORDER BY cnt DESC
            """)
            dept_counts = cur.fetchall()

    return {
        "highest": highest,
        "lowest":  lowest,
        "average": average,
        "total":   total,
        "dept_counts": dept_counts,
    }


def F(size=10, bold=False):
    return tkFont.Font(family="Helvetica", size=size,
                       weight="bold" if bold else "normal")

def style_entry(e):
    e.configure(bg=CARD, fg=TEXT, relief="flat", bd=0,
                highlightthickness=1, highlightbackground=BORDER,
                highlightcolor=PRIMARY, insertbackground=PRIMARY,
                font=F(10))

def style_btn(b, primary=True, danger=False):
    b.configure(bg="#e5e7eb", fg=TEXT, relief="flat", bd=0,
                activebackground="#d1d5db", activeforeground=TEXT,
                cursor="hand2", font=F(10, bold=True))
    b.bind("<Enter>", lambda _: b.config(bg="#d1d5db"))
    b.bind("<Leave>", lambda _: b.config(bg="#e5e7eb"))

def center(win, w, h):
    win.update_idletasks()
    x = (win.winfo_screenwidth()  - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

def labeled_entry(parent, label, var, show="", col=0, row=0):
    tk.Label(parent, text=label, font=F(9, bold=True),
             bg=CARD, fg=SUBTLE).grid(row=row, column=col*2,
                                      sticky="w", padx=(0, 8), pady=4)
    e = tk.Entry(parent, textvariable=var, show=show, width=20)
    style_entry(e)
    e.grid(row=row, column=col*2+1, sticky="ew", ipady=5, pady=4)
    return e
