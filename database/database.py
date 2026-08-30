import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


def get_connection():
    """Get a database connection."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    return conn


def init_database():
    """Initialize database tables."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                brand TEXT,
                price REAL DEFAULT 0,
                quantity INTEGER DEFAULT 0,
                supplier TEXT,
                expiry_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sales table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total REAL NOT NULL,
                sale_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        # Insert default admin user
        cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("admin", "admin123")
            )

        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database init error: {e}")
        import traceback
        traceback.print_exc()


def _verify_schema():
    """Verify the products table has all required columns."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(products)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        
        required = ['id', 'barcode', 'name', 'category', 'brand', 'price', 
                    'quantity', 'supplier', 'expiry_date']
        missing = [col for col in required if col not in columns]
        
        if missing:
            print(f"⚠️ Missing columns in products table: {missing}")
            print(f"   Current columns: {columns}")
            return False
        return True
    except Exception as e:
        print(f"❌ Schema verification error: {e}")
        return False


def authenticate_user(username, password):
    """Check user credentials."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()
        return user is not None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False


def add_product(barcode, name, category, brand, price, quantity, supplier, expiry_date):
    """
    Add or update a product.
    Returns:
        True  → success
        str   → error message (if failed)
    """
    # Input validation
    if not barcode or not str(barcode).strip():
        return "Barcode is required"
    if not name or not str(name).strip():
        return "Product name is required"

    try:
        # Ensure correct data types
        barcode = str(barcode).strip()
        name = str(name).strip()
        category = str(category or "").strip()
        brand = str(brand or "").strip()
        supplier = str(supplier or "").strip()
        expiry_date = str(expiry_date or "").strip()
        
        try:
            price = float(price) if price else 0.0
        except (ValueError, TypeError):
            return f"Invalid price value: {price}"
        
        try:
            quantity = int(quantity) if quantity else 0
        except (ValueError, TypeError):
            return f"Invalid quantity value: {quantity}"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, quantity FROM products WHERE barcode = ?", (barcode,))
        existing = cursor.fetchone()

        if existing:
            # Update existing product (add to quantity)
            new_qty = existing[1] + quantity
            cursor.execute("""
                UPDATE products 
                SET name=?, category=?, brand=?, price=?, quantity=?, supplier=?, expiry_date=?
                WHERE barcode=?
            """, (name, category, brand, price, new_qty, supplier, expiry_date, barcode))
            print(f"✅ Updated product: {name} (new qty: {new_qty})")
        else:
            # Insert new product
            cursor.execute("""
                INSERT INTO products (barcode, name, category, brand, price, quantity, supplier, expiry_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (barcode, name, category, brand, price, quantity, supplier, expiry_date))
            print(f"✅ Added new product: {name}")

        conn.commit()
        conn.close()
        return True

    except sqlite3.IntegrityError as e:
        error_msg = f"Database integrity error: {e}"
        print(f"❌ {error_msg}")
        return error_msg
    except sqlite3.OperationalError as e:
        error_msg = f"Database operational error: {e}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}: {e}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


def get_all_products():
    """Get all products."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        return products
    except Exception as e:
        print(f"❌ Get products error: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_product_by_barcode(barcode):
    """Find a product by barcode."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE barcode = ?", (barcode,))
        product = cursor.fetchone()
        conn.close()
        return product
    except Exception as e:
        print(f"❌ Get product error: {e}")
        return None


def update_product_quantity(barcode, quantity_sold):
    """Reduce quantity after sale."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET quantity = quantity - ? WHERE barcode = ?",
            (quantity_sold, barcode)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Update quantity error: {e}")
        return False


def record_sale(barcode, product_name, quantity, total):
    """Record a sale."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sales (barcode, product_name, quantity, total)
            VALUES (?, ?, ?, ?)
        """, (barcode, product_name, quantity, total))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Record sale error: {e}")
        return False


def get_all_sales():
    """Get all sales."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales ORDER BY sale_date DESC")
        sales = cursor.fetchall()
        conn.close()
        return sales
    except Exception as e:
        print(f"❌ Get sales error: {e}")
        return []


def delete_product(barcode):
    """Delete a product."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE barcode = ?", (barcode,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Delete product error: {e}")
        return False


# Initialize the database on import
init_database()
_verify_schema()