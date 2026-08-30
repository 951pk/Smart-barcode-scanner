import tkinter as tk
from tkinter import ttk, messagebox
import time

import cv2
from PIL import Image, ImageTk

from database.database import (
    add_product, get_all_products, get_all_sales,
    update_product_quantity, record_sale
)


class DashboardWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Barcode Scanner - Inventory Management")
        self.state('zoomed')

        # Inventory camera
        self.camera_scanner = None
        self.camera_running = False
        self.last_scanned_code = ""
        self.barcode_first_seen = None

        # Sales camera
        self.sales_camera_scanner = None
        self.sales_camera_running = False
        self.sales_last_scanned_code = ""
        self.sales_barcode_first_seen = None

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both")

        self.inventory_tab = ttk.Frame(self.notebook)
        self.sales_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.inventory_tab, text="Inventory")
        self.notebook.add(self.sales_tab, text="Sales")

        self._build_inventory_tab()
        self._build_sales_tab()
        self.refresh_data()

        self.bind('<Escape>', lambda e: self.exit_fullscreen())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.stop_camera()
        self.stop_sales_camera()
        self.destroy()

    def exit_fullscreen(self):
        self.state('normal')

    def _build_inventory_tab(self):
        top_frame = ttk.Frame(self.inventory_tab)
        top_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(top_frame, text="Add / Update Product",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=5)

        form = ttk.Frame(top_frame)
        form.pack(fill="x", pady=5)
        fields = [
            ("Barcode", "barcode"),
            ("Product Name", "name"),
            ("Category", "category"),
            ("Brand", "brand"),
            ("Price", "price"),
            ("Quantity", "quantity"),
            ("Supplier", "supplier"),
            ("Expiry Date", "expiry"),
        ]
        self.inventory_vars = {}
        for index, (label_text, key) in enumerate(fields):
            tk.Label(form, text=label_text, font=("Segoe UI", 11)).grid(
                row=index // 2, column=(index % 2) * 2, sticky="w", padx=10, pady=8
            )
            var = tk.StringVar()
            entry = tk.Entry(form, textvariable=var, width=25, font=("Segoe UI", 11))
            entry.grid(row=index // 2, column=(index % 2) * 2 + 1, padx=10, pady=8)
            self.inventory_vars[key] = var
            if key == "barcode":
                self.barcode_entry = entry
                entry.bind("<KeyRelease>", lambda e: self.auto_fill_product_name())

        button_frame = ttk.Frame(top_frame)
        button_frame.pack(pady=12)
        ttk.Button(button_frame, text="Save Product", command=self.save_product).pack(side="left", padx=8)
        ttk.Button(button_frame, text="Clear Form", command=self.clear_form).pack(side="left", padx=8)

        # Camera section
        camera_frame = ttk.LabelFrame(top_frame, text="Live Camera Scanner", padding=10)
        camera_frame.pack(fill="both", expand=True, pady=10)

        button_row = ttk.Frame(camera_frame)
        button_row.pack(pady=10)
        ttk.Button(button_row, text="Start Camera", command=self.start_camera).pack(side="left", padx=8)
        ttk.Button(button_row, text="Stop Camera", command=self.stop_camera).pack(side="left", padx=8)
        ttk.Button(button_row, text="Scan & Save", command=self.scan_and_save).pack(side="left", padx=8)

        status_row = ttk.Frame(camera_frame)
        status_row.pack(pady=5, fill="x")
        self.camera_status = tk.StringVar(value="Camera stopped")
        ttk.Label(status_row, textvariable=self.camera_status,
                  font=("Segoe UI", 12, "bold"), foreground="blue").pack(side="left", padx=10)

        self.barcode_hold_label = tk.StringVar(value="Hold time: 0.0s")
        ttk.Label(status_row, textvariable=self.barcode_hold_label,
                  font=("Segoe UI", 11), foreground="green").pack(side="left", padx=10)

        self.camera_label = tk.Label(camera_frame, bg="black", width=100, height=20,
                                     font=("Segoe UI", 12))
        self.camera_label.pack(padx=10, pady=10, fill="both", expand=True)

        # Inventory table
        table_frame = ttk.LabelFrame(self.inventory_tab, text="Product Inventory", padding=10)
        table_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.product_count_label = tk.StringVar(value="Total Products: 0")
        ttk.Label(table_frame, textvariable=self.product_count_label,
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=5, pady=5)

        self.inventory_tree = ttk.Treeview(
            table_frame,
            columns=("barcode", "name", "qty", "price", "category", "supplier"),
            show="headings",
            height=8,
        )
        for col, text, width in [
            ("barcode", "Barcode", 120),
            ("name", "Product Name", 200),
            ("qty", "Quantity", 80),
            ("price", "Price", 100),
            ("category", "Category", 120),
            ("supplier", "Supplier", 150),
        ]:
            self.inventory_tree.heading(col, text=text)
            self.inventory_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical",
                                  command=self.inventory_tree.yview)
        self.inventory_tree.configure(yscroll=scrollbar.set)
        self.inventory_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_sales_tab(self):
        # Title
        tk.Label(self.sales_tab, text="Sales Transaction",
                 font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=15, pady=10)

        # Sale info section (shows product details after scan)
        self.sale_barcode = tk.StringVar()
        self.sale_quantity = tk.StringVar(value="1")
        self.sale_product_name = tk.StringVar(value="—")
        self.sale_product_price = tk.StringVar(value="—")
        self.sale_product_stock = tk.StringVar(value="—")
        self.sale_total = tk.StringVar(value="$0.00")

        form = ttk.LabelFrame(self.sales_tab, text="Sale Details", padding=10)
        form.pack(fill="x", padx=15, pady=10)

        # Row 0: Barcode + Quantity
        tk.Label(form, text="Barcode:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.sale_barcode_entry = tk.Entry(form, textvariable=self.sale_barcode, font=("Segoe UI", 12), width=25)
        self.sale_barcode_entry.grid(row=0, column=1, padx=10, pady=8)
        self.sale_barcode_entry.bind("<KeyRelease>", lambda e: self._on_sale_barcode_change())

        tk.Label(form, text="Quantity:", font=("Segoe UI", 12)).grid(row=0, column=2, padx=10, pady=8, sticky="w")
        qty_entry = tk.Entry(form, textvariable=self.sale_quantity, font=("Segoe UI", 12), width=10)
        qty_entry.grid(row=0, column=3, padx=10, pady=8)
        qty_entry.bind("<KeyRelease>", lambda e: self._update_sale_total())

        # Row 1: Product info
        tk.Label(form, text="Product:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        tk.Label(form, textvariable=self.sale_product_name, font=("Segoe UI", 12, "bold"),
                 foreground="blue").grid(row=1, column=1, padx=10, pady=8, sticky="w")

        tk.Label(form, text="Price:", font=("Segoe UI", 12)).grid(row=1, column=2, padx=10, pady=8, sticky="w")
        tk.Label(form, textvariable=self.sale_product_price, font=("Segoe UI", 12, "bold"),
                 foreground="green").grid(row=1, column=3, padx=10, pady=8, sticky="w")

        # Row 2: Stock + Total
        tk.Label(form, text="In Stock:", font=("Segoe UI", 12)).grid(row=2, column=0, padx=10, pady=8, sticky="w")
        tk.Label(form, textvariable=self.sale_product_stock, font=("Segoe UI", 12, "bold")).grid(
            row=2, column=1, padx=10, pady=8, sticky="w")

        tk.Label(form, text="Total:", font=("Segoe UI", 12)).grid(row=2, column=2, padx=10, pady=8, sticky="w")
        tk.Label(form, textvariable=self.sale_total, font=("Segoe UI", 14, "bold"),
                 foreground="red").grid(row=2, column=3, padx=10, pady=8, sticky="w")

        # Sell button
        button_frame = ttk.Frame(self.sales_tab)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="💰 Sell Item", command=self.sell_item).pack(side="left", padx=8)
        ttk.Button(button_frame, text="Clear", command=self.clear_sale_form).pack(side="left", padx=8)

        # Sales Camera section
        sales_cam_frame = ttk.LabelFrame(self.sales_tab, text="Live Camera Scanner for Sales", padding=10)
        sales_cam_frame.pack(fill="both", expand=True, padx=15, pady=10)

        sales_button_row = ttk.Frame(sales_cam_frame)
        sales_button_row.pack(pady=5)
        ttk.Button(sales_button_row, text="Start Camera", command=self.start_sales_camera).pack(side="left", padx=8)
        ttk.Button(sales_button_row, text="Stop Camera", command=self.stop_sales_camera).pack(side="left", padx=8)
        ttk.Button(sales_button_row, text="Scan & Sell", command=self.scan_and_sell).pack(side="left", padx=8)

        sales_status_row = ttk.Frame(sales_cam_frame)
        sales_status_row.pack(pady=5, fill="x")
        self.sales_camera_status = tk.StringVar(value="Camera stopped")
        ttk.Label(sales_status_row, textvariable=self.sales_camera_status,
                  font=("Segoe UI", 12, "bold"), foreground="blue").pack(side="left", padx=10)

        self.sales_barcode_hold_label = tk.StringVar(value="Hold time: 0.0s")
        ttk.Label(sales_status_row, textvariable=self.sales_barcode_hold_label,
                  font=("Segoe UI", 11), foreground="green").pack(side="left", padx=10)

        self.sales_camera_label = tk.Label(sales_cam_frame, bg="black", width=100, height=15,
                                           font=("Segoe UI", 12))
        self.sales_camera_label.pack(padx=10, pady=10, fill="both", expand=True)

        # Sales history table
        sales_table_frame = ttk.LabelFrame(self.sales_tab, text="Sales History", padding=10)
        sales_table_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.sales_tree = ttk.Treeview(sales_table_frame,
                                       columns=("barcode", "name", "qty", "total"),
                                       show="headings", height=8)
        self.sales_tree.heading("barcode", text="Barcode")
        self.sales_tree.heading("name", text="Product")
        self.sales_tree.heading("qty", text="Quantity")
        self.sales_tree.heading("total", text="Total ($)")
        
        self.sales_tree.column("barcode", width=150)
        self.sales_tree.column("name", width=250)
        self.sales_tree.column("qty", width=100)
        self.sales_tree.column("total", width=120)

        sales_scrollbar = ttk.Scrollbar(sales_table_frame, orient="vertical",
                                        command=self.sales_tree.yview)
        self.sales_tree.configure(yscroll=sales_scrollbar.set)
        self.sales_tree.pack(side="left", fill="both", expand=True)
        sales_scrollbar.pack(side="right", fill="y")

    # ============================================================
    # INVENTORY CAMERA METHODS
    # ============================================================
    def start_camera(self):
        if self.camera_running:
            self.camera_status.set("⚠️ Camera already running")
            return

        try:
            from scanner.scanner import CameraScanner

            self.camera_scanner = CameraScanner(0)
            if not self.camera_scanner.is_open():
                self.camera_status.set("❌ Camera not available")
                messagebox.showerror("Camera error", "Could not open camera.")
                self.camera_scanner = None
                return

            self.camera_running = True
            self.camera_status.set("📹 Camera starting...")
            self.barcode_first_seen = None
            self.after(100, self._update_camera_preview)
        except Exception as e:
            self.camera_status.set(f"❌ Camera error")
            messagebox.showerror("Camera Error", f"Failed to start camera: {str(e)}")
            import traceback
            traceback.print_exc()

    def stop_camera(self):
        self.camera_running = False
        self.camera_status.set("⏹️ Camera stopped")
        if self.camera_scanner is not None:
            self.camera_scanner.release()
            self.camera_scanner = None
        try:
            self.camera_label.configure(image="")
            self.camera_label.image = None
        except:
            pass
        self.barcode_hold_label.set("Hold time: 0.0s")
        self.barcode_first_seen = None

    def _update_camera_preview(self):
        if not self.camera_running or self.camera_scanner is None:
            return

        try:
            frame, decoded_values = self.camera_scanner.read_frame()
            if frame is None or frame.size == 0:
                self.after(30, self._update_camera_preview)
                return

            if decoded_values:
                scanned_code = decoded_values[0]
                if scanned_code != self.last_scanned_code:
                    self.last_scanned_code = scanned_code
                    self.barcode_first_seen = time.time()
                    self.inventory_vars["barcode"].set(scanned_code)
                    self.auto_fill_product_name()
                    self.camera_status.set(f"✅ Scanned: {scanned_code}")
                else:
                    if self.barcode_first_seen:
                        hold_time = time.time() - self.barcode_first_seen
                        self.barcode_hold_label.set(f"Hold time: {hold_time:.1f}s")
            else:
                self.barcode_first_seen = None
                self.barcode_hold_label.set("Hold time: 0.0s")

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb_frame, (900, 500))
            pil_image = Image.fromarray(resized)
            photo = ImageTk.PhotoImage(pil_image)
            self.camera_label.configure(image=photo)
            self.camera_label.image = photo
        except Exception as e:
            print(f"Camera preview error: {e}")

        if self.winfo_exists() and self.camera_running:
            self.after(30, self._update_camera_preview)

    # ============================================================
    # SALES CAMERA METHODS
    # ============================================================
    def start_sales_camera(self):
        if self.sales_camera_running:
            self.sales_camera_status.set("⚠️ Camera already running")
            return

        # Stop inventory camera if running (only one can use camera at a time)
        if self.camera_running:
            self.stop_camera()

        try:
            from scanner.scanner import CameraScanner

            self.sales_camera_scanner = CameraScanner(0)
            if not self.sales_camera_scanner.is_open():
                self.sales_camera_status.set("❌ Camera not available")
                messagebox.showerror("Camera error", "Could not open camera.")
                self.sales_camera_scanner = None
                return

            self.sales_camera_running = True
            self.sales_camera_status.set("📹 Camera starting...")
            self.sales_barcode_first_seen = None
            self.after(100, self._update_sales_camera_preview)
        except Exception as e:
            self.sales_camera_status.set(f"❌ Camera error")
            messagebox.showerror("Camera Error", f"Failed to start camera: {str(e)}")
            import traceback
            traceback.print_exc()

    def stop_sales_camera(self):
        self.sales_camera_running = False
        self.sales_camera_status.set("⏹️ Camera stopped")
        if self.sales_camera_scanner is not None:
            self.sales_camera_scanner.release()
            self.sales_camera_scanner = None
        try:
            self.sales_camera_label.configure(image="")
            self.sales_camera_label.image = None
        except:
            pass
        self.sales_barcode_hold_label.set("Hold time: 0.0s")
        self.sales_barcode_first_seen = None

    def _update_sales_camera_preview(self):
        if not self.sales_camera_running or self.sales_camera_scanner is None:
            return

        try:
            frame, decoded_values = self.sales_camera_scanner.read_frame()
            if frame is None or frame.size == 0:
                self.after(30, self._update_sales_camera_preview)
                return

            if decoded_values:
                scanned_code = decoded_values[0]
                if scanned_code != self.sales_last_scanned_code:
                    self.sales_last_scanned_code = scanned_code
                    self.sales_barcode_first_seen = time.time()
                    self.sale_barcode.set(scanned_code)
                    self._on_sale_barcode_change()
                    self.sales_camera_status.set(f"✅ Scanned: {scanned_code}")
                else:
                    if self.sales_barcode_first_seen:
                        hold_time = time.time() - self.sales_barcode_first_seen
                        self.sales_barcode_hold_label.set(f"Hold time: {hold_time:.1f}s")
            else:
                self.sales_barcode_first_seen = None
                self.sales_barcode_hold_label.set("Hold time: 0.0s")

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb_frame, (900, 400))
            pil_image = Image.fromarray(resized)
            photo = ImageTk.PhotoImage(pil_image)
            self.sales_camera_label.configure(image=photo)
            self.sales_camera_label.image = photo
        except Exception as e:
            print(f"Sales camera preview error: {e}")

        if self.winfo_exists() and self.sales_camera_running:
            self.after(30, self._update_sales_camera_preview)

    # ============================================================
    # INVENTORY METHODS
    # ============================================================
    def auto_fill_product_name(self):
        """Auto-fill all product fields from database if barcode exists."""
        barcode = self.inventory_vars["barcode"].get().strip()
        if not barcode:
            return

        for item in get_all_products():
            if item[1] == barcode:
                self.inventory_vars["name"].set(item[2] or "")
                self.inventory_vars["category"].set(item[3] or "")
                self.inventory_vars["brand"].set(item[4] or "")
                self.inventory_vars["price"].set(str(item[5]) if item[5] else "")
                self.inventory_vars["supplier"].set(item[7] or "")
                self.inventory_vars["expiry"].set(item[8] or "")
                break

    def clear_form(self):
        for var in self.inventory_vars.values():
            var.set("")
        self.last_scanned_code = ""
        self.barcode_hold_label.set("Hold time: 0.0s")
        self.barcode_first_seen = None

    def scan_and_save(self):
        barcode = self.inventory_vars["barcode"].get().strip()
        name = self.inventory_vars["name"].get().strip()
        if not barcode:
            messagebox.showerror("Input error", "Barcode is required")
            return
        if not name:
            messagebox.showerror("Input error", "Product Name is required")
            return

        try:
            price = float(self.inventory_vars["price"].get() or 0)
            quantity = int(self.inventory_vars["quantity"].get() or 1)
        except ValueError:
            messagebox.showerror("Input error", "Price and quantity must be numeric")
            return

        result = add_product(
            barcode, name,
            self.inventory_vars["category"].get().strip(),
            self.inventory_vars["brand"].get().strip(),
            price, quantity,
            self.inventory_vars["supplier"].get().strip(),
            self.inventory_vars["expiry"].get().strip(),
        )

        if result is True:
            messagebox.showinfo("Saved", f"✅ Product '{name}' saved successfully")
            self.last_scanned_code = ""
            self.barcode_first_seen = None
            self.clear_form()
            self.refresh_data()
        else:
            messagebox.showerror("Database Error", f"Could not save product:\n\n{result}")

    def save_product(self):
        barcode = self.inventory_vars["barcode"].get().strip()
        name = self.inventory_vars["name"].get().strip()

        if not barcode:
            messagebox.showerror("Input error", "Barcode is required")
            return
        if not name:
            messagebox.showerror("Input error", "Product Name is required")
            return

        try:
            price = float(self.inventory_vars["price"].get() or 0)
            quantity = int(self.inventory_vars["quantity"].get() or 0)
        except ValueError:
            messagebox.showerror("Input error", "Price and quantity must be numeric")
            return

        result = add_product(
            barcode, name,
            self.inventory_vars["category"].get().strip(),
            self.inventory_vars["brand"].get().strip(),
            price, quantity,
            self.inventory_vars["supplier"].get().strip(),
            self.inventory_vars["expiry"].get().strip(),
        )

        if result is True:
            messagebox.showinfo("Saved", f"✅ Product '{name}' saved successfully")
            self.refresh_data()
            self.clear_form()
        else:
            messagebox.showerror("Database Error", f"Could not save product:\n\n{result}")

    # ============================================================
    # SALES METHODS
    # ============================================================
    def _on_sale_barcode_change(self):
        """Auto-lookup product details when barcode is entered/scanned."""
        barcode = self.sale_barcode.get().strip()
        if not barcode:
            self.sale_product_name.set("—")
            self.sale_product_price.set("—")
            self.sale_product_stock.set("—")
            self.sale_total.set("$0.00")
            return

        product = None
        for item in get_all_products():
            if item[1] == barcode:
                product = item
                break

        if product:
            self.sale_product_name.set(product[2])
            self.sale_product_price.set(f"${float(product[5]):.2f}")
            self.sale_product_stock.set(str(product[6]))
            self._update_sale_total()
        else:
            self.sale_product_name.set("❌ Not found")
            self.sale_product_price.set("—")
            self.sale_product_stock.set("—")
            self.sale_total.set("$0.00")

    def _update_sale_total(self):
        """Calculate and display sale total."""
        try:
            barcode = self.sale_barcode.get().strip()
            qty = int(self.sale_quantity.get() or 0)
            
            for item in get_all_products():
                if item[1] == barcode:
                    total = float(item[5]) * qty
                    self.sale_total.set(f"${total:.2f}")
                    return
            self.sale_total.set("$0.00")
        except (ValueError, TypeError):
            self.sale_total.set("$0.00")

    def clear_sale_form(self):
        """Clear sale form fields."""
        self.sale_barcode.set("")
        self.sale_quantity.set("1")
        self.sale_product_name.set("—")
        self.sale_product_price.set("—")
        self.sale_product_stock.set("—")
        self.sale_total.set("$0.00")
        self.sales_last_scanned_code = ""
        self.sales_barcode_first_seen = None
        self.sales_barcode_hold_label.set("Hold time: 0.0s")

    def scan_and_sell(self):
        """Quick sell after scanning."""
        if not self.sale_barcode.get().strip():
            messagebox.showerror("Input error", "Please scan a barcode first")
            return
        self.sell_item()

    def sell_item(self):
        try:
            quantity = int(self.sale_quantity.get())
            if quantity <= 0:
                messagebox.showerror("Input error", "Quantity must be greater than 0")
                return
        except ValueError:
            messagebox.showerror("Input error", "Quantity must be numeric")
            return

        barcode = self.sale_barcode.get().strip()
        if not barcode:
            messagebox.showerror("Input error", "Barcode is required")
            return

        product = None
        for item in get_all_products():
            if item[1] == barcode:
                product = item
                break

        if product is None:
            messagebox.showerror("Not found", "Barcode not found in inventory")
            return

        if product[6] < quantity:
            messagebox.showerror("Insufficient stock",
                                 f"Only {product[6]} item(s) in stock. Cannot sell {quantity}.")
            return

        total = float(product[5]) * quantity
        if update_product_quantity(barcode, quantity) and record_sale(barcode, product[2], quantity, total):
            messagebox.showinfo("Sale complete",
                                f"✅ Sold {quantity} × {product[2]}\n\nTotal: ${total:.2f}")
            self.refresh_data()
            self.clear_sale_form()
        else:
            messagebox.showerror("Error", "Could not record sale")

    def refresh_data(self):
        # Refresh inventory table
        for row in self.inventory_tree.get_children():
            self.inventory_tree.delete(row)
        products = get_all_products()
        for product in products:
            self.inventory_tree.insert(
                "", "end",
                values=(product[1], product[2], product[6],
                        f"${product[5]:.2f}", product[3] or "-", product[7] or "-"),
            )
        self.product_count_label.set(f"Total Products: {len(products)}")

        # Refresh sales table
        for row in self.sales_tree.get_children():
            self.sales_tree.delete(row)
        for sale in get_all_sales():
            self.sales_tree.insert("", "end",
                                   values=(sale[1], sale[2], sale[3], f"${sale[4]:.2f}"))