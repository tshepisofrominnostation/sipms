# ============================================================
# SIPMS — Smart Inventory & Procurement Management System
# Built by: Tshepiso Freddy Thosago | Rem0Beg Solutions
# Stack: Python 3.11, Flask 3.0, PostgreSQL (prod) / SQLite (dev)
# ============================================================
#
# HOW THIS FILE WORKS (for interview explanations):
# --------------------------------------------------
# This is the main Flask application file. Think of Flask as a
# lightweight web server framework. Each @app.route() decorator
# tells Flask: "when someone visits this URL, run this function
# and return a page or JSON response."
#
# We use SQLite locally (simple file-based DB, no setup needed)
# and PostgreSQL on Render.com (production-grade relational DB).
# The DATABASE_URL environment variable switches between them.
# ============================================================

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
import os
import csv
import io
from datetime import datetime

# -- Database drivers ----------------------------------------
# We support two databases:
#   - SQLite  (local dev)   — just a file, zero config
#   - PostgreSQL (Render)   — real production database
# The get_db() function returns the right connection each time.
try:
    import psycopg2
    import psycopg2.extras
    USING_POSTGRES = bool(os.environ.get('DATABASE_URL'))
except ImportError:
    USING_POSTGRES = False

import sqlite3

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)

# secret_key is used by Flask to sign session cookies.
# In production this should be a random 32-char string from env vars.
app.secret_key = os.environ.get('SECRET_KEY', 'sipms-dev-secret-change-in-prod')

# Work out which database to connect to.
# On Render.com, DATABASE_URL is set automatically when you add a
# PostgreSQL service. Locally we just use a SQLite file.
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    # Render gives us a URL starting with "postgres://" but psycopg2
    # needs "postgresql://" — this one-liner fixes that.
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db():
    """
    Open and return a database connection.

    We use a context-manager pattern: open, use, close.
    This avoids leaving idle connections open (a common mistake
    that causes "too many connections" errors in production).

    For PostgreSQL, RealDictCursor makes rows behave like
    Python dicts instead of plain tuples — same as SQLite's
    row_factory = sqlite3.Row.
    """
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
    else:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sipms.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # lets us do row['column_name']
    return conn


def query(sql, params=(), one=False):
    """
    Run a SELECT query and return the results.

    'one=True' returns a single row (used for detail pages).
    'one=False' returns a list of all matching rows (used for tables).

    Parameterised queries (?  for SQLite, %s for Postgres) are how
    we prevent SQL injection — never build SQL strings with f-strings.
    """
    # Postgres uses %s placeholders, SQLite uses ?
    if DATABASE_URL:
        sql = sql.replace('?', '%s')

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = cur.fetchone() if one else cur.fetchall()
        return result
    finally:
        conn.close()  # always close, even if an error occurs


def execute(sql, params=()):
    """
    Run an INSERT, UPDATE, or DELETE and commit the change.

    We wrap everything in a try/except so if something goes wrong
    we roll back the transaction — leaving the DB in a clean state.
    This is the ACID principle: Atomicity (all or nothing).
    """
    if DATABASE_URL:
        sql = sql.replace('?', '%s')

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()   # make the change permanent
    except Exception as e:
        conn.rollback() # undo everything if something fails
        raise e
    finally:
        conn.close()


def executemany(sql, param_list):
    """
    Run the same SQL statement for a list of parameter sets.
    Used for bulk inserts (e.g. seeding demo data).
    """
    if DATABASE_URL:
        sql = sql.replace('?', '%s')

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.executemany(sql, param_list)
        conn.commit()
    finally:
        conn.close()


# ============================================================
# DATABASE INITIALISATION
# ============================================================

def init_db():
    """
    Create all tables if they don't exist yet, then seed demo data.

    'CREATE TABLE IF NOT EXISTS' is safe to run on every startup —
    it only creates the table the very first time (idempotent).

    We check if suppliers already exist before seeding so we don't
    duplicate data on every restart.
    """
    conn = get_db()
    cur = conn.cursor()

    # -- SUPPLIERS table --
    # Stores who we buy stock from.
    cur.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_name TEXT    NOT NULL,
            email         TEXT,
            phone         TEXT,
            address       TEXT,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    ''') if not DATABASE_URL else cur.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id   SERIAL PRIMARY KEY,
            supplier_name TEXT    NOT NULL,
            email         TEXT,
            phone         TEXT,
            address       TEXT,
            created_at    TIMESTAMP DEFAULT NOW()
        )
    ''')

    # -- PRODUCTS table --
    # Each product has a cost price (what we paid) and selling price
    # (what we charge). reorder_level triggers a low-stock alert.
    cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name  TEXT    NOT NULL,
            category      TEXT,
            quantity      INTEGER DEFAULT 0,
            cost_price    REAL    DEFAULT 0,
            selling_price REAL    DEFAULT 0,
            reorder_level INTEGER DEFAULT 10,
            supplier_id   INTEGER REFERENCES suppliers(supplier_id),
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    ''') if not DATABASE_URL else cur.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id    SERIAL  PRIMARY KEY,
            product_name  TEXT    NOT NULL,
            category      TEXT,
            quantity      INTEGER DEFAULT 0,
            cost_price    NUMERIC(12,2) DEFAULT 0,
            selling_price NUMERIC(12,2) DEFAULT 0,
            reorder_level INTEGER DEFAULT 10,
            supplier_id   INTEGER REFERENCES suppliers(supplier_id),
            created_at    TIMESTAMP DEFAULT NOW()
        )
    ''')

    # -- PURCHASE ORDERS table --
    # A PO is a formal request sent to a supplier to buy stock.
    # Status flow: Pending → Approved → Closed
    cur.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id   INTEGER REFERENCES suppliers(supplier_id),
            order_date    TEXT,
            status        TEXT DEFAULT 'Pending',
            total_amount  REAL DEFAULT 0,
            notes         TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    ''') if not DATABASE_URL else cur.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            po_id         SERIAL  PRIMARY KEY,
            supplier_id   INTEGER REFERENCES suppliers(supplier_id),
            order_date    DATE,
            status        TEXT    DEFAULT 'Pending',
            total_amount  NUMERIC(12,2) DEFAULT 0,
            notes         TEXT,
            created_at    TIMESTAMP DEFAULT NOW()
        )
    ''')

    # -- PO ITEMS table --
    # Each PO can contain multiple line items (products + quantities).
    # This is a classic many-to-many bridge table.
    cur.execute('''
        CREATE TABLE IF NOT EXISTS po_items (
            item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id      INTEGER REFERENCES purchase_orders(po_id),
            product_id INTEGER REFERENCES products(product_id),
            quantity   INTEGER,
            unit_price REAL
        )
    ''') if not DATABASE_URL else cur.execute('''
        CREATE TABLE IF NOT EXISTS po_items (
            item_id    SERIAL  PRIMARY KEY,
            po_id      INTEGER REFERENCES purchase_orders(po_id),
            product_id INTEGER REFERENCES products(product_id),
            quantity   INTEGER,
            unit_price NUMERIC(12,2)
        )
    ''')

    # -- INVENTORY TRANSACTIONS table --
    # Every stock movement is recorded here — received, issued, adjusted.
    # This gives us a full audit trail (who moved what, when, and why).
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            transaction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id       INTEGER REFERENCES products(product_id),
            quantity         INTEGER,
            transaction_type TEXT,
            reference        TEXT,
            notes            TEXT,
            transaction_date TEXT DEFAULT (datetime('now'))
        )
    ''') if not DATABASE_URL else cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            transaction_id   SERIAL    PRIMARY KEY,
            product_id       INTEGER   REFERENCES products(product_id),
            quantity         INTEGER,
            transaction_type TEXT,
            reference        TEXT,
            notes            TEXT,
            transaction_date TIMESTAMP DEFAULT NOW()
        )
    ''')

    conn.commit()

    # -- Seed demo data (only on first run) --
    existing = cur.execute('SELECT COUNT(*) FROM suppliers').fetchone()
    count = existing[0]  # works for both sqlite3.Row and psycopg2 RealDictRow

    if count == 0:
        suppliers = [
            ('TechSupply SA',        'orders@techsupply.co.za', '011 234 5678', 'Johannesburg, GP'),
            ('ProStock Distributors','info@prostock.co.za',     '021 987 6543', 'Cape Town, WC'),
            ('Vanguard Wholesale',   'sales@vanguard.co.za',    '031 456 7890', 'Durban, KZN'),
        ]
        cur.executemany(
            'INSERT INTO suppliers (supplier_name, email, phone, address) VALUES (?, ?, ?, ?)' if not DATABASE_URL
            else 'INSERT INTO suppliers (supplier_name, email, phone, address) VALUES (%s, %s, %s, %s)',
            suppliers
        )

        products = [
            ('Laptop HP 250 G9',       'Electronics', 45, 8500,  12000, 10, 1),
            ('Office Chair Ergonomic', 'Furniture',   30, 2200,  3500,   5, 2),
            ('A4 Paper Ream 80gsm',    'Stationery',   8,   65,    95,  20, 3),
            ('Samsung Monitor 24"',    'Electronics', 22, 4200,  6500,   8, 1),
            ('USB-C Hub 7-Port',       'Electronics', 55,  350,   599,  15, 1),
            ('Desk Lamp LED',          'Furniture',   18,  280,   450,  10, 2),
            ('Printer Cartridge Black','Stationery',   6,  320,   520,  25, 3),
            ('Wireless Keyboard',      'Electronics', 40,  550,   899,  12, 1),
        ]
        sql = ('INSERT INTO products (product_name,category,quantity,cost_price,selling_price,reorder_level,supplier_id) VALUES (?,?,?,?,?,?,?)'
               if not DATABASE_URL else
               'INSERT INTO products (product_name,category,quantity,cost_price,selling_price,reorder_level,supplier_id) VALUES (%s,%s,%s,%s,%s,%s,%s)')
        cur.executemany(sql, products)

        pos = [
            (1, '2026-05-10', 'Approved', 42500),
            (2, '2026-05-18', 'Pending',  18700),
            (3, '2026-06-01', 'Closed',    9800),
            (1, '2026-06-05', 'Pending',  31200),
        ]
        sql = ('INSERT INTO purchase_orders (supplier_id,order_date,status,total_amount) VALUES (?,?,?,?)'
               if not DATABASE_URL else
               'INSERT INTO purchase_orders (supplier_id,order_date,status,total_amount) VALUES (%s,%s,%s,%s)')
        cur.executemany(sql, pos)

        txns = [
            (1, 20, 'Received',   'PO-001', 'Initial laptop stock'),
            (2, 15, 'Received',   'PO-001', 'Initial chair stock'),
            (3, 50, 'Received',   'PO-003', 'Bulk paper order'),
            (1,  5, 'Issued',     'REQ-001','Sales order fulfillment'),
            (4, 10, 'Received',   'PO-001', 'Monitor restock'),
            (7, 10, 'Issued',     'REQ-002','IT department request'),
            (3, 10, 'Adjustment', 'ADJ-001','Stock count correction after audit'),
        ]
        sql = ('INSERT INTO inventory_transactions (product_id,quantity,transaction_type,reference,notes) VALUES (?,?,?,?,?)'
               if not DATABASE_URL else
               'INSERT INTO inventory_transactions (product_id,quantity,transaction_type,reference,notes) VALUES (%s,%s,%s,%s,%s)')
        cur.executemany(sql, txns)
        conn.commit()

    conn.close()


# ============================================================
# TEMPLATE CONTEXT PROCESSOR
# ============================================================

@app.context_processor
def inject_now():
    # Makes 'now' available in every template automatically
    # Used in base.html to show the current date/time in the topbar
    return {'now': datetime.now().strftime('%d %b %Y, %H:%M')}


# ============================================================
# ROUTE: DASHBOARD  —  GET /
# ============================================================

@app.route('/')
def dashboard():
    """
    The main dashboard shows a high-level snapshot of the business:
    - KPI cards (totals, stock value, alerts)
    - Low stock warnings
    - Recent stock movements
    - Purchase order status breakdown
    - Stock value by category

    All of this is read from the DB in a single function call.
    We avoid N+1 queries by doing JOINs rather than looping in Python.
    """

    # Basic KPI counts
    total_products  = query('SELECT COUNT(*) as n FROM products',      one=True)['n']
    total_suppliers = query('SELECT COUNT(*) as n FROM suppliers',     one=True)['n']
    pending_pos     = query("SELECT COUNT(*) as n FROM purchase_orders WHERE status='Pending'", one=True)['n']
    low_stock_count = query('SELECT COUNT(*) as n FROM products WHERE quantity <= reorder_level', one=True)['n']

    # Financial totals
    stock_value   = query('SELECT COALESCE(SUM(quantity * cost_price), 0) as v FROM products',          one=True)['v']
    pending_value = query("SELECT COALESCE(SUM(total_amount), 0) as v FROM purchase_orders WHERE status='Pending'", one=True)['v']

    # Products that need reordering — joined with supplier so we know who to call
    low_stock_items = query('''
        SELECT p.product_name, p.quantity, p.reorder_level, s.supplier_name
        FROM   products p
        LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
        WHERE  p.quantity <= p.reorder_level
        ORDER BY p.quantity ASC
        LIMIT 5
    ''')

    # Last 8 stock movements — most recent first
    recent_transactions = query('''
        SELECT t.transaction_type, t.quantity, t.transaction_date,
               p.product_name, t.reference
        FROM   inventory_transactions t
        JOIN   products p ON t.product_id = p.product_id
        ORDER BY t.transaction_date DESC
        LIMIT 8
    ''')

    # PO breakdown grouped by status (Pending / Approved / Closed)
    po_summary = query('''
        SELECT status,
               COUNT(*)                          AS cnt,
               COALESCE(SUM(total_amount), 0)    AS total
        FROM   purchase_orders
        GROUP BY status
    ''')

    # Stock value breakdown by product category
    category_stock = query('''
        SELECT category,
               COUNT(*)                       AS products,
               SUM(quantity)                  AS total_qty,
               SUM(quantity * cost_price)     AS value
        FROM   products
        GROUP BY category
        ORDER BY value DESC
    ''')

    return render_template('dashboard.html',
        total_products=total_products,
        total_suppliers=total_suppliers,
        pending_pos=pending_pos,
        low_stock=low_stock_count,
        stock_value=stock_value,
        pending_value=pending_value,
        low_stock_items=low_stock_items,
        recent_transactions=recent_transactions,
        po_summary=po_summary,
        category_stock=category_stock
    )


# ============================================================
# ROUTES: PRODUCTS
# ============================================================

@app.route('/products')
def products():
    """
    Show all products with optional search and category filter.

    We build the SQL query dynamically using a params list — this is
    the safe way to handle user input (parameterised queries).
    Never do: WHERE name = '" + search + "' — that's SQL injection.
    """
    search   = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    # Start with a base query that always works (WHERE 1=1 is a trick
    # that lets us safely append AND clauses without special-casing the first one)
    sql    = '''SELECT p.*, s.supplier_name
                FROM   products p
                LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
                WHERE  1=1'''
    params = []

    if search:
        sql += ' AND p.product_name LIKE ?'
        params.append(f'%{search}%')     # % is the SQL wildcard

    if category:
        sql += ' AND p.category = ?'
        params.append(category)

    sql += ' ORDER BY p.product_name'

    if DATABASE_URL:
        sql = sql.replace('?', '%s')

    all_products = query(sql, params)
    all_suppliers = query('SELECT * FROM suppliers ORDER BY supplier_name')
    all_categories = query('SELECT DISTINCT category FROM products ORDER BY category')

    return render_template('products.html',
        products=all_products,
        suppliers=all_suppliers,
        categories=all_categories,
        search=search,
        selected_category=category
    )


@app.route('/products/add', methods=['POST'])
def add_product():
    """Add a new product from the form submission."""
    name          = request.form['product_name'].strip()
    category      = request.form['category'].strip()
    quantity      = int(request.form.get('quantity', 0))
    cost_price    = float(request.form.get('cost_price', 0))
    selling_price = float(request.form.get('selling_price', 0))
    reorder_level = int(request.form.get('reorder_level', 10))
    supplier_id   = request.form.get('supplier_id') or None  # None if blank

    execute('''INSERT INTO products
               (product_name, category, quantity, cost_price, selling_price, reorder_level, supplier_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (name, category, quantity, cost_price, selling_price, reorder_level, supplier_id))

    flash(f'"{name}" added to inventory.', 'success')
    return redirect(url_for('products'))


@app.route('/products/edit/<int:pid>', methods=['POST'])
def edit_product(pid):
    """Update an existing product. The product ID comes from the URL."""
    execute('''UPDATE products
               SET product_name=?, category=?, cost_price=?, selling_price=?, reorder_level=?, supplier_id=?
               WHERE product_id=?''',
            (request.form['product_name'], request.form['category'],
             float(request.form.get('cost_price', 0)), float(request.form.get('selling_price', 0)),
             int(request.form.get('reorder_level', 10)), request.form.get('supplier_id') or None, pid))

    flash('Product updated successfully.', 'success')
    return redirect(url_for('products'))


@app.route('/products/delete/<int:pid>', methods=['POST'])
def delete_product(pid):
    """Delete a product by ID. We use POST (not GET) for destructive actions."""
    execute('DELETE FROM products WHERE product_id = ?', (pid,))
    flash('Product removed from inventory.', 'info')
    return redirect(url_for('products'))


# ============================================================
# ROUTES: SUPPLIERS
# ============================================================

@app.route('/suppliers')
def suppliers():
    """List all suppliers with a count of their linked products."""
    all_suppliers = query('''
        SELECT s.*, COUNT(p.product_id) AS product_count
        FROM   suppliers s
        LEFT JOIN products p ON p.supplier_id = s.supplier_id
        GROUP BY s.supplier_id, s.supplier_name, s.email, s.phone, s.address, s.created_at
        ORDER BY s.supplier_name
    ''')
    return render_template('suppliers.html', suppliers=all_suppliers)


@app.route('/suppliers/add', methods=['POST'])
def add_supplier():
    name    = request.form['supplier_name'].strip()
    email   = request.form.get('email', '').strip()
    phone   = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()

    execute('INSERT INTO suppliers (supplier_name, email, phone, address) VALUES (?, ?, ?, ?)',
            (name, email, phone, address))

    flash(f'Supplier "{name}" added.', 'success')
    return redirect(url_for('suppliers'))


@app.route('/suppliers/edit/<int:sid>', methods=['POST'])
def edit_supplier(sid):
    execute('UPDATE suppliers SET supplier_name=?, email=?, phone=?, address=? WHERE supplier_id=?',
            (request.form['supplier_name'], request.form.get('email', ''),
             request.form.get('phone', ''), request.form.get('address', ''), sid))
    flash('Supplier updated.', 'success')
    return redirect(url_for('suppliers'))


@app.route('/suppliers/<int:sid>/history')
def supplier_history(sid):
    """Show a supplier's purchase history and linked products."""
    supplier = query('SELECT * FROM suppliers WHERE supplier_id = ?', (sid,), one=True)
    pos      = query('SELECT * FROM purchase_orders WHERE supplier_id = ? ORDER BY order_date DESC', (sid,))
    prods    = query('SELECT * FROM products WHERE supplier_id = ?', (sid,))
    return render_template('supplier_history.html', supplier=supplier, pos=pos, products=prods)


# ============================================================
# ROUTES: PURCHASE ORDERS
# ============================================================

@app.route('/purchase-orders')
def purchase_orders():
    """
    List all purchase orders with their supplier names.
    We use a LEFT JOIN so POs without a supplier still show up.
    """
    all_pos = query('''
        SELECT po.*, s.supplier_name
        FROM   purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
        ORDER BY po.order_date DESC
    ''')
    all_suppliers = query('SELECT * FROM suppliers ORDER BY supplier_name')
    all_products  = query('SELECT * FROM products ORDER BY product_name')
    return render_template('purchase_orders.html',
        purchase_orders=all_pos,
        suppliers=all_suppliers,
        products=all_products
    )


@app.route('/purchase-orders/add', methods=['POST'])
def add_purchase_order():
    """
    Create a new PO. We calculate the total from the line items
    so the number is always accurate — never trust a hidden form field for money.
    """
    supplier_id  = request.form['supplier_id']
    order_date   = request.form['order_date']
    notes        = request.form.get('notes', '').strip()
    product_ids  = request.form.getlist('product_id[]')
    quantities   = request.form.getlist('quantity[]')
    unit_prices  = request.form.getlist('unit_price[]')

    # Calculate total from line items
    total = sum(
        int(qty) * float(price)
        for qty, price in zip(quantities, unit_prices)
        if qty and price
    )

    # Insert the PO header first
    conn = get_db()
    cur  = conn.cursor()

    if DATABASE_URL:
        cur.execute(
            'INSERT INTO purchase_orders (supplier_id, order_date, total_amount, notes) VALUES (%s, %s, %s, %s) RETURNING po_id',
            (supplier_id, order_date, total, notes)
        )
        po_id = cur.fetchone()['po_id']
    else:
        cur.execute(
            'INSERT INTO purchase_orders (supplier_id, order_date, total_amount, notes) VALUES (?, ?, ?, ?)',
            (supplier_id, order_date, total, notes)
        )
        po_id = cur.lastrowid

    # Then insert each line item
    for pid, qty, price in zip(product_ids, quantities, unit_prices):
        if pid and qty and price:
            sql = ('INSERT INTO po_items (po_id, product_id, quantity, unit_price) VALUES (%s,%s,%s,%s)'
                   if DATABASE_URL else
                   'INSERT INTO po_items (po_id, product_id, quantity, unit_price) VALUES (?,?,?,?)')
            cur.execute(sql, (po_id, pid, int(qty), float(price)))

    conn.commit()
    conn.close()

    flash(f'Purchase Order #{po_id} created — R{total:,.2f} total.', 'success')
    return redirect(url_for('purchase_orders'))


@app.route('/purchase-orders/<int:po_id>/approve', methods=['POST'])
def approve_po(po_id):
    """Approve a PO — moves status from Pending to Approved."""
    execute("UPDATE purchase_orders SET status='Approved' WHERE po_id=?", (po_id,))
    flash(f'PO #{po_id} approved.', 'success')
    return redirect(url_for('purchase_orders'))


@app.route('/purchase-orders/<int:po_id>/close', methods=['POST'])
def close_po(po_id):
    """
    Close a PO and automatically update stock quantities.

    This is the key business logic: when goods are received (PO closed),
    we add the ordered quantities to each product's stock level and
    record a transaction in the audit trail.
    """
    # Get all line items for this PO
    items = query('SELECT * FROM po_items WHERE po_id = ?', (po_id,))

    for item in items:
        pid = item['product_id']
        qty = item['quantity']

        # Add received quantity to stock
        execute('UPDATE products SET quantity = quantity + ? WHERE product_id = ?', (qty, pid))

        # Record the receipt in the transaction audit trail
        execute('''INSERT INTO inventory_transactions (product_id, quantity, transaction_type, reference, notes)
                   VALUES (?, ?, 'Received', ?, 'Auto-received on PO closure')''',
                (pid, qty, f'PO-{po_id}'))

    # Mark the PO as closed
    execute("UPDATE purchase_orders SET status='Closed' WHERE po_id=?", (po_id,))
    flash(f'PO #{po_id} closed — stock updated automatically.', 'success')
    return redirect(url_for('purchase_orders'))


# ============================================================
# ROUTES: INVENTORY TRANSACTIONS
# ============================================================

@app.route('/transactions')
def transactions():
    """
    Full audit trail of every stock movement.
    Joined with products so we show the product name, not just an ID.
    """
    all_txns = query('''
        SELECT t.*, p.product_name
        FROM   inventory_transactions t
        JOIN   products p ON t.product_id = p.product_id
        ORDER BY t.transaction_date DESC
    ''')
    all_products = query('SELECT * FROM products ORDER BY product_name')
    return render_template('transactions.html', transactions=all_txns, products=all_products)


@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    """
    Record a manual stock movement (receive, issue, or adjustment).

    - Received:   stock goes UP
    - Issued:     stock goes DOWN
    - Adjustment: can go either way (we subtract because adjustment
                  values can be negative if entered correctly)
    """
    product_id = int(request.form['product_id'])
    quantity   = int(request.form['quantity'])
    txn_type   = request.form['transaction_type']   # Received / Issued / Adjustment
    reference  = request.form.get('reference', '').strip()
    notes      = request.form.get('notes', '').strip()

    # Update stock based on transaction type
    if txn_type == 'Received':
        execute('UPDATE products SET quantity = quantity + ? WHERE product_id = ?', (quantity, product_id))
    elif txn_type == 'Issued':
        execute('UPDATE products SET quantity = quantity - ? WHERE product_id = ?', (quantity, product_id))
    # Adjustments are logged but the caller must ensure quantity is correct

    # Always write to the audit trail regardless of type
    execute('''INSERT INTO inventory_transactions
               (product_id, quantity, transaction_type, reference, notes)
               VALUES (?, ?, ?, ?, ?)''',
            (product_id, quantity, txn_type, reference, notes))

    flash(f'Transaction recorded — {txn_type} x{quantity} units.', 'success')
    return redirect(url_for('transactions'))


# ============================================================
# ROUTES: REPORTS
# ============================================================

@app.route('/reports')
def reports():
    """
    Management reports page.
    All data is pre-aggregated in SQL so the template stays simple.
    """

    # Full inventory valuation — cost price vs selling price per product
    inventory_report = query('''
        SELECT p.product_name, p.category, p.quantity,
               p.cost_price, p.selling_price,
               (p.quantity * p.cost_price)    AS stock_cost_value,
               (p.quantity * p.selling_price) AS stock_sell_value,
               s.supplier_name
        FROM   products p
        LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
        ORDER BY stock_cost_value DESC
    ''')

    # How much we've spent per supplier (only closed/approved POs)
    supplier_spend = query('''
        SELECT s.supplier_name, s.email,
               COUNT(po.po_id)             AS total_orders,
               COALESCE(SUM(po.total_amount), 0) AS total_spend
        FROM   suppliers s
        LEFT JOIN purchase_orders po
               ON s.supplier_id = po.supplier_id
              AND po.status IN ('Approved', 'Closed')
        GROUP BY s.supplier_id, s.supplier_name, s.email
        ORDER BY total_spend DESC
    ''')

    # Purchase order history with status
    po_report = query('''
        SELECT po.po_id, po.order_date, po.status, po.total_amount, s.supplier_name
        FROM   purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
        ORDER BY po.order_date DESC
    ''')

    # Summary totals for the report header
    totals = {
        'stock_cost':  sum(row['stock_cost_value']  for row in inventory_report),
        'stock_sell':  sum(row['stock_sell_value']   for row in inventory_report),
        'total_spend': sum(row['total_spend']        for row in supplier_spend),
    }

    return render_template('reports.html',
        inventory_report=inventory_report,
        supplier_spend=supplier_spend,
        po_report=po_report,
        totals=totals
    )


@app.route('/reports/export/<report_type>')
def export_csv(report_type):
    """
    Export any report as a CSV file.

    We use Python's csv module to write to an in-memory buffer (io.StringIO)
    and return it as a file download — no temp files needed on the server.

    The Content-Disposition header is what tells the browser to download
    rather than display the response.
    """

    output  = io.StringIO()
    writer  = csv.writer(output)
    today   = datetime.now().strftime('%Y-%m-%d')

    if report_type == 'inventory':
        writer.writerow(['Product', 'Category', 'Qty', 'Cost Price', 'Sell Price', 'Cost Value', 'Sell Value', 'Supplier'])
        rows = query('''
            SELECT p.product_name, p.category, p.quantity, p.cost_price, p.selling_price,
                   (p.quantity * p.cost_price), (p.quantity * p.selling_price), s.supplier_name
            FROM products p LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
        ''')
        for row in rows:
            writer.writerow(list(row))
        filename = f'sipms_inventory_{today}.csv'

    elif report_type == 'suppliers':
        writer.writerow(['Supplier', 'Email', 'Total Orders', 'Total Spend (R)'])
        rows = query('''
            SELECT s.supplier_name, s.email, COUNT(po.po_id), COALESCE(SUM(po.total_amount), 0)
            FROM suppliers s LEFT JOIN purchase_orders po ON s.supplier_id = po.supplier_id
            GROUP BY s.supplier_id, s.supplier_name, s.email
        ''')
        for row in rows:
            writer.writerow(list(row))
        filename = f'sipms_supplier_spend_{today}.csv'

    elif report_type == 'po':
        writer.writerow(['PO #', 'Supplier', 'Order Date', 'Status', 'Total (R)'])
        rows = query('''
            SELECT po.po_id, s.supplier_name, po.order_date, po.status, po.total_amount
            FROM purchase_orders po LEFT JOIN suppliers s ON po.supplier_id = s.supplier_id
            ORDER BY po.order_date DESC
        ''')
        for row in rows:
            writer.writerow(list(row))
        filename = f'sipms_purchase_orders_{today}.csv'

    else:
        flash('Unknown report type.', 'danger')
        return redirect(url_for('reports'))

    # Build the HTTP response with file download headers
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Content-Type'] = 'text/csv'
    return response


# ============================================================
# APP STARTUP
# ============================================================

# init_db() runs once when the app starts — creates tables + seeds data
with app.app_context():
    init_db()

if __name__ == '__main__':
    # debug=True gives us live reload and detailed error pages in development.
    # NEVER run with debug=True in production — it exposes the debugger.
    app.run(debug=True, port=5000)
