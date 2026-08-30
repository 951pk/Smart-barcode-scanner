import tkinter as tk
from tkinter import ttk, messagebox
from database.database import authenticate_user


class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Barcode Scanner - Login")
        self.geometry("450x350")
        self.configure(bg="#f0f0f0")
        self.resizable(False, False)

        # Center the window
        self.eval('tk::PlaceWindow . center')

        self._build_ui()

    def _build_ui(self):
        # Title
        title = tk.Label(
            self,
            text="🔒 Smart Barcode Scanner",
            font=("Segoe UI", 18, "bold"),
            bg="#f0f0f0",
            fg="#2c3e50"
        )
        title.pack(pady=30)

        subtitle = tk.Label(
            self,
            text="Please login to continue",
            font=("Segoe UI", 11),
            bg="#f0f0f0",
            fg="#7f8c8d"
        )
        subtitle.pack(pady=5)

        # Form
        form_frame = tk.Frame(self, bg="#f0f0f0")
        form_frame.pack(pady=20)

        tk.Label(form_frame, text="Username:", font=("Segoe UI", 11),
                 bg="#f0f0f0").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.username_var = tk.StringVar(value="admin")
        tk.Entry(form_frame, textvariable=self.username_var, font=("Segoe UI", 11),
                 width=25).grid(row=0, column=1, padx=10, pady=8)

        tk.Label(form_frame, text="Password:", font=("Segoe UI", 11),
                 bg="#f0f0f0").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        self.password_var = tk.StringVar(value="admin123")
        tk.Entry(form_frame, textvariable=self.password_var, font=("Segoe UI", 11),
                 width=25, show="*").grid(row=1, column=1, padx=10, pady=8)

        # Buttons
        button_frame = tk.Frame(self, bg="#f0f0f0")
        button_frame.pack(pady=15)

        ttk.Button(button_frame, text="Login", command=self.login).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Exit", command=self.destroy).pack(side="left", padx=10)

        # Info label
        info = tk.Label(
            self,
            text="Default: admin / admin123",
            font=("Segoe UI", 9, "italic"),
            bg="#f0f0f0",
            fg="#95a5a6"
        )
        info.pack(pady=10)

        # Bind Enter key
        self.bind('<Return>', lambda e: self.login())

    def login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return

        if authenticate_user(username, password):
            self.destroy()
            from gui.dashboard import DashboardWindow
            dashboard = DashboardWindow()
            dashboard.mainloop()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")