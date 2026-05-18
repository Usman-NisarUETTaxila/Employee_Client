from Constants import *
from helper_functions import *
from Register import RegisterWindow
from Dashboard import DashboardWindow

class LoginWindow:
    def __init__(self, root):
        self.root = root
        root.title("Log In")
        root.configure(bg=BG)
        root.resizable(False, False)
        center(root, 420, 400)
        self._build()

    def _build(self):
        bg_frame = tk.Frame(self.root, bg=BG)
        bg_frame.pack(expand=True, fill="both")

        card = tk.Frame(bg_frame, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", width=360)

        p = tk.Frame(card, bg=CARD)
        p.pack(fill="both", expand=True, padx=36, pady=36)

        tk.Label(p, text="Log In", font=F(20, bold=True),
                 bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(p, text="Employee Management System",
                 font=F(10), bg=CARD, fg=SUBTLE).pack(anchor="w", pady=(2, 22))

        self.u  = tk.StringVar()
        self.pw = tk.StringVar()

        for label, var, show in [("Username", self.u, ""), ("Password", self.pw, "•")]:
            tk.Label(p, text=label, font=F(10, bold=True),
                     bg=CARD, fg=TEXT).pack(anchor="w")
            e = tk.Entry(p, textvariable=var, show=show)
            style_entry(e)
            e.pack(fill="x", ipady=7, pady=(4, 14))

        self.msg = tk.Label(p, text="", font=F(9), bg=CARD, fg=ERR,
                            wraplength=280, justify="left")
        self.msg.pack(anchor="w", pady=(0, 8))

        btn = tk.Button(p, text="Log In", command=self._login)
        style_btn(btn)
        btn.pack(fill="x", ipady=9)


        self.root.bind("<Return>", lambda _: self._login())

    def _login(self):
        u = self.u.get().strip()
        p = self.pw.get().strip()
        if not u or not p:
            self.msg.config(text="Please fill in all fields.", fg=ERR); return
        self.msg.config(text="Connecting…", fg=SUBTLE)
        self.root.update_idletasks()
        try:
            user = db_login(u, p)
        except Exception as e:
            self.msg.config(text=f"Connection error:\n{e}", fg=ERR); return
        if user:
            self.root.destroy()
            DashboardWindow(tk.Tk(), user)
        else:
            self.msg.config(text="Invalid username or password.", fg=ERR)