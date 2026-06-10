from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response
import sqlite3
import os
import csv
import io
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'sipms-rem0beg-2024-secret'

DB_PATH = 'sipms.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT,
        quantity INTEGER DEFAULT 0,
        cost_price REAL DEFAULT 0,
        selling_price REAL DEFAULT 0,
        reorder_level INTEGER DEFAULT 10,
        supplier_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS purchase_orders (
        po_id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id INTEGER,
        order_date TEXT,
        status TEXT DEFAULT 'Pending',
        total_amount REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS po_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        po_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price REAL,
        FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        quantity INTEGER,
        transaction_type TEXT,
        reference TEXT,
        notes TEXT,
        transaction_date TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )''')
    count = c.execute('SELECT COUNT(*) FROM suppliers').fetchone()[0]
    if count == 0:
        suppliers = [
            ('TechSupply SA', 'orders@techsupply.co.za', '011 234 5678', 'Johannesburg, GP'),
            ('ProStock Distributors', 'info@prostock.co.za', '021 987 6543', 'Cape Town, WC'),
            ('Vanguard Wholesale', 'sales@vanguard.co.za', '031 456 7890', 'Durban, KZN'),
        ]
        c.executemany('INSERT INTO suppliers (supplier_name,email,phone,address) VALUES (?,?,?,?)', suppliers)
        products = [
            ('Laptop HP 250 G9', 'Electronics', 45, 8500, 12000, 10, 1),
            ('Office Chair Ergonomic', 'Furniture', 30, 2200, 3500, 5, 2),
            ('A4 Paper Ream 80gsm', 'Stationery', 8, 65, 95, 20, 3),
            ('Samsung Monitor 24"', 'Electronics', 22, 4200, 6500, 8, 1),
            ('USB-C Hub 7-Port', 'Electronics', 55, 350, 599, 15, 1),
            ('Desk Lamp LED', 'Furniture', 18, 280, 450, 10, 2),
            ('Printer Cartridge Black', 'Stationery', 6, 320, 520, 25, 3),
            ('Wireless Keyboard', 'Electronics', 40, 550, 899, 12, 1),
        ]
        c.executemany('INSERT INTO products (product_name,category,quantity,cost_price,selling_price,reorder_level,supplier_id) VALUES (?,?,?,?,?,?,?)', products)
        pos = [
            (1, '2024-05-10', 'Approved', 42500),
            (2, '2024-05-18', 'Pending', 18700),
            (3, '2024-06-01', 'Closed', 9800),
            (1, '2024-06-05', 'Pending', 31200),
        ]
        c.executemany('INSERT INTO purchase_orders (supplier_id,order_date,status,total_amount) VALUES (?,?,?,?)', pos)
        txns = [
            (1, 20, 'Received', 'PO-001', 'Initial stock'),
            (2, 15, 'Received', 'PO-001', 'Initial stock'),
            (3, 50, 'Received', 'PO-003', 'Bulk order'),
            (1, 5, 'Issued', 'REQ-001', 'Sales order'),
            (4, 10, 'Received', 'PO-001', 'Restock'),
            (7, 10, 'Issued', 'REQ-002', 'Department request'),
            (3, 10, 'Adjustment', 'ADJ-001', 'Stock count correction'),
        ]
        c.executemany('INSERT INTO inventory_transactions (product_id,quantity,transaction_type,reference,notes) VALUES (?,?,?,?,?)', txns)
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    conn = get_db()
    total_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    total_suppliers = conn.execute('SELECT COUNT(*) FROM suppliers').fetchone()[0]
    pending_pos = conn.execute("SELECT COUNT(*) FROM purchase_orders WHERE status='Pending'").fetchone()[0]
    low_stock = conn.execute('SELECT COUNT(*) FROM products WHERE quantity <= reorder_level').fetchone()[0]
    stock_value = conn.execute('SELECT COALESCE(SUM(quantity * cost_price),0) FROM products').fetchone()[0]
    pending_value = conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM purchase_orders WHERE status='Pending'").fetchone()[0]
    low_stock_items = conn.execute('''SELECT p.product_name, p.quantity, p.reorder_level, s.supplier_name
        FROM products p LEFT JOIN suppliers s ON p.supplier_id=s.supplier_id
        WHERE p.quantity <= p.reorder_level ORDER BY p.quantity ASC LIMIT 5''').fetchall()
    recent_txns = conn.execute('''SELECT t.transaction_type, t.quantity, t.transaction_date, p.product_name, t.reference
        FROM inventory_transactions t JOIN products p ON t.product_id=p.product_id
        ORDER BY t.transaction_date DESC LIMIT 8''').fetchall()
    po_summary = conn.execute('''SELECT status, COUNT(*) as cnt, COALESCE(SUM(total_amount),0) as total
        FROM purchase_orders GROUP BY status''').fetchall()
    category_stock = conn.execute('''SELECT category, COUNT(*) as products, SUM(quantity) as total_qty, SUM(quantity*cost_price) as value
        FROM products GROUP BY category ORDER BY value DESC''').fetchall()
    conn.close()
    return render_template('dashboard.html', total_products=total_products, total_suppliers=total_suppliers,
        pending_pos=pending_pos, low_stock=low_stock, stock_value=stock_value, pending_value=pending_value,
        low_stock_items=low_stock_items, recent_txns=recent_txns, po_summary=po_summary, category_stock=category_stock)

@app.route('/products')
def products():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    conn = get_db()
    query = 'SELECT p.*, s.supplier_name FROM products p LEFT JOIN suppliers s ON p.supplier_id=s.supplier_id WHERE 1=1'
    params = []
    if search:
        query += ' AND p.product_name LIKE ?'
        params.append(f'%{search}%')
    if category:
        query += ' AND p.category=?'
        params.append(category)
    query += ' ORDER BY p.product_name'
    prods = conn.execute(query, params).fetchall()
    suppliers = conn.execute('SELECT * FROM suppliers ORDER BY supplier_name').fetchall()
    categories = conn.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    conn.close()
    return render_template('products.html', products=prods, suppliers=suppliers,
                           categories=categories, search=search, selected_category=category)

@app.route('/products/add', methods=['POST'])
def add_product():
    conn = get_db()
    conn.execute('INSERT INTO products (product_name,category,quantity,cost_price,selling_price,reorder_level,supplier_id) VALUES (?,?,?,?,?,?,?)',
        (request.form['product_name'], request.form['category'], int(request.form.get('quantity',0)),
         float(request.form.get('cost_price',0)), float(request.form.get('selling_price',0)),
         int(request.form.get('reorder_level',10)), request.form.get('supplier_id') or None))
    conn.commit(); conn.close()
    flash('Product added successfully.', 'success')
    return redirect(url_for('products'))

@app.route('/products/edit/<int:pid>', methods=['POST'])
def edit_product(pid):
    conn = get_db()
    conn.execute('UPDATE products SET product_name=?,category=?,cost_price=?,selling_price=?,reorder_level=?,supplier_id=? WHERE product_id=?',
        (request.form['product_name'], request.form['category'], float(request.form.get('cost_price',0)),
         float(request.form.get('selling_price',0)), int(request.form.get('reorder_level',10)),
         request.form.get('supplier_id') or None, pid))
    conn.commit(); conn.close()
    flash('Product updated.', 'success')
    return redirect(url_for('products'))

@app.route('/products/delete/<int:pid>', methods=['POST'])
def delete_product(pid):
    conn = get_db()
    conn.execute('DELETE FROM products WHERE product_id=?', (pid,))
    conn.commit(); conn.close()
    flash('Product deleted.', 'info')
    return redirect(url_for('products'))

@app.route('/suppliers')
def suppliers():
    conn = get_db()
    sups = conn.execute('SELECT * FROM suppliers ORDER BY supplier_name').fetchall()
    conn.close()
    return render_template('suppliers.html', suppliers=sups)

@app.route('/suppliers/add', methods=['POST'])
def add_supplier():
    conn = get_db()
    conn.execute('INSERT INTO suppliers (supplier_name,email,phone,address) VALUES (?,?,?,?)',
        (request.form['supplier_name'], request.form.get('email',''), request.form.get('phone',''), request.form.get('address','')))
    conn.commit(); conn.close()
    flash('Supplier added.', 'success')
    return redirect(url_for('suppliers'))

@app.route('/suppliers/edit/<int:sid>', methods=['POST'])
def edit_supplier(sid):
    conn = get_db()
    conn.execute('UPDATE suppliers SET supplier_name=?,email=?,phone=?,address=? WHERE supplier_id=?',
        (request.form['supplier_name'], request.form.get('email',''), request.form.get('phone',''),
         request.form.get('address',''), sid))
    conn.commit(); conn.close()
    flash('Supplier updated.', 'success')
    return redirect(url_for('suppliers'))

@app.route('/suppliers/<int:sid>/history')
def supplier_history(sid):
    conn = get_db()
    supplier = conn.execute('SELECT * FROM suppliers WHERE supplier_id=?', (sid,)).fetchone()
    pos = conn.execute('SELECT * FROM purchase_orders WHERE supplier_id=? ORDER BY order_date DESC', (sid,)).fetchall()
    prods = conn.execute('SELECT * FROM products WHERE supplier_id=?', (sid,)).fetchall()
    conn.close()
    return render_template('supplier_history.html', supplier=supplier, pos=pos, products=prods)

@app.route('/purchase-orders')
def purchase_orders():
    conn = get_db()
    pos = conn.execute('''SELECT po.*, s.supplier_name FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id=s.supplier_id ORDER BY po.order_date DESC''').fetchall()
    sups = conn.execute('SELECT * FROM suppliers ORDER BY supplier_name').fetchall()
    prods = conn.execute('SELECT * FROM products ORDER BY product_name').fetchall()
    conn.close()
    return render_template('purchase_orders.html', pos=pos, suppliers=sups, products=prods)

@app.route('/purchase-orders/add', methods=['POST'])
def add_po():
    conn = get_db()
    cur = conn.execute('INSERT INTO purchase_orders (supplier_id,order_date,status,total_amount,notes) VALUES (?,?,?,?,?)',
        (request.form['supplier_id'], request.form.get('order_date', str(date.today())), 'Pending', 0, request.form.get('notes','')))
    po_id = cur.lastrowid
    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    prices = request.form.getlist('unit_price[]')
    total = 0
    for pid, qty, price in zip(product_ids, quantities, prices):
        if pid and qty:
            q, p = int(qty), float(price or 0)
            conn.execute('INSERT INTO po_items (po_id,product_id,quantity,unit_price) VALUES (?,?,?,?)', (po_id, int(pid), q, p))
            total += q * p
    conn.execute('UPDATE purchase_orders SET total_amount=? WHERE po_id=?', (total, po_id))
    conn.commit(); conn.close()
    flash(f'Purchase Order PO-{po_id:04d} created.', 'success')
    return redirect(url_for('purchase_orders'))

@app.route('/purchase-orders/<int:poid>/approve', methods=['POST'])
def approve_po(poid):
    conn = get_db()
    conn.execute("UPDATE purchase_orders SET status='Approved' WHERE po_id=?", (poid,))
    conn.commit(); conn.close()
    flash(f'PO-{poid:04d} approved.', 'success')
    return redirect(url_for('purchase_orders'))

@app.route('/purchase-orders/<int:poid>/close', methods=['POST'])
def close_po(poid):
    conn = get_db()
    items = conn.execute('SELECT * FROM po_items WHERE po_id=?', (poid,)).fetchall()
    for item in items:
        conn.execute('UPDATE products SET quantity = quantity + ? WHERE product_id=?', (item['quantity'], item['product_id']))
        conn.execute('INSERT INTO inventory_transactions (product_id,quantity,transaction_type,reference,notes) VALUES (?,?,?,?,?)',
            (item['product_id'], item['quantity'], 'Received', f'PO-{poid:04d}', 'Goods received from PO'))
    conn.execute("UPDATE purchase_orders SET status='Closed' WHERE po_id=?", (poid,))
    conn.commit(); conn.close()
    flash(f'PO-{poid:04d} closed. Stock updated.', 'success')
    return redirect(url_for('purchase_orders'))

@app.route('/purchase-orders/<int:poid>')
def po_detail(poid):
    conn = get_db()
    po = conn.execute('''SELECT po.*, s.supplier_name FROM purchase_orders po
        LEFT JOIN suppliers s ON po.supplier_id=s.supplier_id WHERE po.po_id=?''', (poid,)).fetchone()
    items = conn.execute('''SELECT pi.*, p.product_name FROM po_items pi
        JOIN products p ON pi.product_id=p.product_id WHERE pi.po_id=?''', (poid,)).fetchall()
    conn.close()
    return render_template('po_detail.html', po=po, items=items)

@app.route('/inventory')
def inventory():
    conn = get_db()
    txns = conn.execute('''SELECT t.*, p.product_name FROM inventory_transactions t
        JOIN products p ON t.product_id=p.product_id ORDER BY t.transaction_date DESC LIMIT 100''').fetchall()
    prods = conn.execute('SELECT * FROM products ORDER BY product_name').fetchall()
    conn.close()
    return render_template('inventory.html', txns=txns, products=prods)

@app.route('/inventory/adjust', methods=['POST'])
def adjust_inventory():
    conn = get_db()
    pid = int(request.form['product_id'])
    qty = int(request.form['quantity'])
    txn_type = request.form['transaction_type']
    ref = request.form.get('reference', '')
    notes = request.form.get('notes', '')
    if txn_type == 'Issued':
        conn.execute('UPDATE products SET quantity = quantity - ? WHERE product_id=?', (qty, pid))
    elif txn_type == 'Received':
        conn.execute('UPDATE products SET quantity = quantity + ? WHERE product_id=?', (qty, pid))
    elif txn_type == 'Adjustment':
        new_qty = int(request.form.get('new_quantity', qty))
        conn.execute('UPDATE products SET quantity=? WHERE product_id=?', (new_qty, pid))
        qty = new_qty
    conn.execute('INSERT INTO inventory_transactions (product_id,quantity,transaction_type,reference,notes) VALUES (?,?,?,?,?)',
        (pid, qty, txn_type, ref, notes))
    conn.commit(); conn.close()
    flash('Inventory transaction recorded.', 'success')
    return redirect(url_for('inventory'))

@app.route('/reports')
def reports():
    conn = get_db()
    inventory_report = conn.execute('''SELECT p.product_name, p.category, p.quantity, p.cost_price, p.selling_price,
        p.reorder_level, s.supplier_name, (p.quantity * p.cost_price) as stock_value,
        CASE WHEN p.quantity <= p.reorder_level THEN 'Low Stock' ELSE 'OK' END as status
        FROM products p LEFT JOIN suppliers s ON p.supplier_id=s.supplier_id ORDER BY p.category, p.product_name''').fetchall()
    supplier_report = conn.execute('''SELECT s.supplier_name, s.email, s.phone,
        COUNT(DISTINCT po.po_id) as total_pos, COUNT(DISTINCT p.product_id) as total_products,
        COALESCE(SUM(po.total_amount),0) as total_spend
        FROM suppliers s LEFT JOIN purchase_orders po ON s.supplier_id=po.supplier_id
        LEFT JOIN products p ON s.supplier_id=p.supplier_id GROUP BY s.supplier_id ORDER BY total_spend DESC''').fetchall()
    po_report = conn.execute('''SELECT po.po_id, po.order_date, po.status, po.total_amount, s.supplier_name, po.notes
        FROM purchase_orders po LEFT JOIN suppliers s ON po.supplier_id=s.supplier_id ORDER BY po.order_date DESC''').fetchall()
    conn.close()
    return render_template('reports.html', inventory_report=inventory_report,
                           supplier_report=supplier_report, po_report=po_report)

@app.route('/reports/export/<report_type>')
def export_report(report_type):
    conn = get_db()
    output = io.StringIO()
    writer = csv.writer(output)
    if report_type == 'inventory':
        writer.writerow(['Product','Category','Qty','Cost Price','Selling Price','Reorder Level','Supplier','Stock Value','Status'])
        rows = conn.execute('''SELECT p.product_name,p.category,p.quantity,p.cost_price,p.selling_price,
            p.reorder_level,s.supplier_name,(p.quantity*p.cost_price),
            CASE WHEN p.quantity<=p.reorder_level THEN 'Low Stock' ELSE 'OK' END
            FROM products p LEFT JOIN suppliers s ON p.supplier_id=s.supplier_id''').fetchall()
        for r in rows: writer.writerow(list(r))
        filename = 'sipms_inventory_report.csv'
    elif report_type == 'po':
        writer.writerow(['PO ID','Order Date','Status','Supplier','Total Amount','Notes'])
        rows = conn.execute('''SELECT po.po_id,po.order_date,po.status,s.supplier_name,po.total_amount,po.notes
            FROM purchase_orders po LEFT JOIN suppliers s ON po.supplier_id=s.supplier_id''').fetchall()
        for r in rows: writer.writerow(list(r))
        filename = 'sipms_po_report.csv'
    elif report_type == 'suppliers':
        writer.writerow(['Supplier','Email','Phone','Total POs','Total Products','Total Spend'])
        rows = conn.execute('''SELECT s.supplier_name,s.email,s.phone,COUNT(DISTINCT po.po_id),
            COUNT(DISTINCT p.product_id),COALESCE(SUM(po.total_amount),0)
            FROM suppliers s LEFT JOIN purchase_orders po ON s.supplier_id=po.supplier_id
            LEFT JOIN products p ON s.supplier_id=p.supplier_id GROUP BY s.supplier_id''').fetchall()
        for r in rows: writer.writerow(list(r))
        filename = 'sipms_supplier_report.csv'
    else:
        conn.close()
        return 'Invalid report type', 400
    conn.close()
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/api/products')
def api_products():
    conn = get_db()
    prods = conn.execute('SELECT product_id, product_name, cost_price FROM products ORDER BY product_name').fetchall()
    conn.close()
    return jsonify([dict(p) for p in prods])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
