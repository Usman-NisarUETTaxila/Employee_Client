from Constants import *
from helper_functions import *
from tkinter import messagebox

class RegisterWindow:
    def __init__(self, root):
        self.root = root
        root.title("Create Account")
        root.configure(bg=BG)
        root.resizable(False, False)
        root.grab_set()
        center(root, 420, 460)
        self._build()

    def _build(self):
        bg_frame = tk.Frame(self.root, bg=BG)
        bg_frame.pack(expand=True, fill="both")

        card = tk.Frame(bg_frame, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", width=360)

        p = tk.Frame(card, bg=CARD)
        p.pack(fill="both", expand=True, padx=36, pady=36)

        tk.Label(p, text="Create Account", font=F(20, bold=True),
                 bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(p, text="Fill in the form below to register.",
                 font=F(10), bg=CARD, fg=SUBTLE).pack(anchor="w", pady=(2, 22))

        self.u  = tk.StringVar()
        self.p1 = tk.StringVar()
        self.p2 = tk.StringVar()

        for label, var, show in [
            ("Username", self.u, ""),
            ("Password", self.p1, "•"),
            ("Confirm Password", self.p2, "•"),
        ]:
            tk.Label(p, text=label, font=F(10, bold=True),
                     bg=CARD, fg=TEXT).pack(anchor="w")
            e = tk.Entry(p, textvariable=var, show=show)
            style_entry(e)
            e.pack(fill="x", ipady=7, pady=(4, 14))

        tk.Label(p, text="Role", font=F(10, bold=True),
                 bg=CARD, fg=TEXT).pack(anchor="w")
        self.role_var = tk.StringVar(value="user")
        rf = tk.Frame(p, bg=CARD)
        rf.pack(fill="x", pady=(4, 16))
        for val, lbl in [("user", "User"), ("admin", "Admin")]:
            tk.Radiobutton(rf, text=lbl, variable=self.role_var, value=val,
                           bg=CARD, fg=TEXT, selectcolor=CARD,
                           activebackground=CARD, font=F(10),
                           cursor="hand2").pack(side="left", padx=(0, 18))

        self.msg = tk.Label(p, text="", font=F(9), bg=CARD, fg=ERR,
                            wraplength=280, justify="left")
        self.msg.pack(anchor="w", pady=(0, 8))

        btn = tk.Button(p, text="Create Account", command=self._register)
        style_btn(btn)
        btn.pack(fill="x", ipady=9)
        self.root.bind("<Return>", lambda _: self._register())

    def _register(self):
        u  = self.u.get().strip()
        p1 = self.p1.get().strip()
        p2 = self.p2.get().strip()
        r  = self.role_var.get()
        if not all([u, p1, p2]):
            self.msg.config(text="Please fill in all fields.", fg=ERR); return
        if p1 != p2:
            self.msg.config(text="Passwords do not match.", fg=ERR); return
        if len(p1) < 6:
            self.msg.config(text="Password must be at least 6 characters.", fg=ERR); return
        self.msg.config(text="Registering…", fg=SUBTLE)
        self.root.update_idletasks()
        ok, reason = db_register(u, p1, r)
        if ok:
            messagebox.showinfo("Success", "Account created! You can now sign in.",
                                parent=self.root)
            self.root.destroy()
        else:
            self.msg.config(text=reason, fg=ERR)