import tkinter as tk
from tkinter import messagebox

from database.database import add_product


class ProductWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Manage Product")
        self.geometry("420x320")

        entries = {}
        fields = [
            ("Barcode", "barcode"),
            ("Product Name", "name"),
            ("Category", "category"),
            ("Price", "price"),
            ("Quantity", "quantity"),
        ]
        for index, (label_text, key) in enumerate(fields):
            tk.Label(self, text=label_text).grid(row=index, column=0, sticky="w", padx=10, pady=5)
            var = tk.StringVar()
            tk.Entry(self, textvariable=var).grid(row=index, column=1, padx=10, pady=5)
            entries[key] = var

        tk.Button(self, text="Save", command=lambda: self.save(entries)).grid(row=len(fields), column=0, columnspan=2, pady=10)

    def save(self, entries):
        try:
            price = float(entries["price"].get())
            quantity = int(entries["quantity"].get())
        except ValueError:
            messagebox.showerror("Input error", "Price and quantity must be numeric")
            return

        add_product(entries["barcode"].get(), entries["name"].get(), entries["category"].get(), "", price, quantity, "", "")
        messagebox.showinfo("Saved", "Product saved")
        self.destroy()
