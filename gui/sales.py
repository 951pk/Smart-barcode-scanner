import tkinter as tk
from tkinter import ttk

from database.database import get_all_sales


class SalesWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sales")
        self.geometry("700x420")

        self.tree = ttk.Treeview(self, columns=("barcode", "name", "qty", "total"), show="headings")
        self.tree.heading("barcode", text="Barcode")
        self.tree.heading("name", text="Product")
        self.tree.heading("qty", text="Qty")
        self.tree.heading("total", text="Total")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for sale in get_all_sales():
            self.tree.insert("", "end", values=(sale[1], sale[2], sale[3], sale[4]))
