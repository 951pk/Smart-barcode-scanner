from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import cv2
import numpy as np
import zxingcpp
import sqlite3
import os
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'smart-barcode-scanner-secret-key-change-in-production')

DB_NAME = 'inventory.db'

# ──────────────────────────────────────────────
# DATABASE HELPERS
# ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin'
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            brand TEXT,
            price REAL DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            supplier TEXT,
            expiry_date TEXT
        );
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            price REAL DEFAULT 0,
            total REAL DEFAULT 0,
            sold_at TEXT DEFAULT (datetime('now','localtime'))
        );
    ''')
    # Seed default admin user
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    conn.execute(
        'INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)',
        ('admin', admin_hash, 'admin')
    )
    conn.commit()
    conn.close()

init_db()

# ──────────────────────────────────────────────
# AUTHENTICATION
# ──────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password_hash = ?',
            (username, pw_hash)
        ).fetchone()
        conn.close()
        if user:
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ──────────────────────────────────────────────
# PAGES
# ──────────────────────────────────────────────
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'])

# ──────────────────────────────────────────────
# PRODUCT API
# ──────────────────────────────────────────────
@app.route('/api/products', methods=['GET'])
@login_required
def get_products():
    conn = get_db()
    products = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    data = request.json
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO products (barcode, name, category, brand, price, quantity, supplier, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('barcode', ''),
            data.get('name', ''),
            data.get('category', ''),
            data.get('brand', ''),
            float(data.get('price', 0)),
            int(data.get('quantity', 0)),
            data.get('supplier', ''),
            data.get('expiry_date', '')
        ))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Product added successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Barcode already exists'}), 400
    finally:
        conn.close()

@app.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    data = request.json
    conn = get_db()
    conn.execute('''
        UPDATE products SET barcode=?, name=?, category=?, brand=?, price=?, quantity=?, supplier=?, expiry_date=?
        WHERE id=?
    ''', (
        data.get('barcode', ''),
        data.get('name', ''),
        data.get('category', ''),
        data.get('brand', ''),
        float(data.get('price', 0)),
        int(data.get('quantity', 0)),
        data.get('supplier', ''),
        data.get('expiry_date', ''),
        product_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Product updated'})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Product deleted'})

# ──────────────────────────────────────────────
# BARCODE SCAN API (image upload)
# ──────────────────────────────────────────────
@app.route('/api/scan', methods=['POST'])
@login_required
def scan_barcode():
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image provided'}), 400

    file = request.files['image']
    npimg = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if img is None:
        return jsonify({'status': 'error', 'message': 'Invalid image'}), 400

       results = zxingcpp.read_barcodes(img)
    if results:
        barcode_data = results[0].text
        # Check if product exists
        conn = get_db()
        product = conn.execute('SELECT * FROM products WHERE barcode = ?', (barcode_data,)).fetchone()
        conn.close()
        return jsonify({
            'status': 'success',
            'barcode': barcode_data,
            'product': dict(product) if product else None
        })
    return jsonify({'status': 'success', 'barcode': None, 'product': None})

# ──────────────────────────────────────────────
# SALES API
# ──────────────────────────────────────────────
@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    conn = get_db()
    sales = conn.execute('SELECT * FROM sales ORDER BY id DESC LIMIT 100').fetchall()
    conn.close()
    return jsonify([dict(s) for s in sales])

@app.route('/api/sales', methods=['POST'])
@login_required
def record_sale():
    data = request.json
    barcode = data.get('barcode', '')
    quantity = int(data.get('quantity', 1))

    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE barcode = ?', (barcode,)).fetchone()
    if not product:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Product not found'}), 404

    if product['quantity'] < quantity:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Insufficient stock'}), 400

    price = product['price']
    total = price * quantity

    conn.execute('''
        INSERT INTO sales (barcode, product_name, quantity, price, total)
        VALUES (?, ?, ?, ?, ?)
    ''', (barcode, product['name'], quantity, price, total))

    conn.execute(
        'UPDATE products SET quantity = quantity - ? WHERE barcode = ?',
        (quantity, barcode)
    )
    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'message': f'Sale recorded: {quantity} x {product["name"]}'})

# ──────────────────────────────────────────────
# DASHBOARD STATS
# ──────────────────────────────────────────────
@app.route('/api/stats')
@login_required
def get_stats():
    conn = get_db()
    total_products = conn.execute('SELECT COUNT(*) as cnt FROM products').fetchone()['cnt']
    total_sales = conn.execute('SELECT COALESCE(SUM(total), 0) as total FROM sales').fetchone()['total']
    total_transactions = conn.execute('SELECT COUNT(*) as cnt FROM sales').fetchone()['cnt']
    low_stock = conn.execute('SELECT COUNT(*) as cnt FROM products WHERE quantity <= 5').fetchone()['cnt']
    conn.close()
    return jsonify({
        'total_products': total_products,
        'total_sales': round(total_sales, 2),
        'total_transactions': total_transactions,
        'low_stock': low_stock
    })

# ──────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))