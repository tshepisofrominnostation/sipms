# 📦 SIPMS — Smart Inventory & Procurement Management System

> Built by **Tshepiso Freddy Thosago** | Rem0Beg Solutions
> *A full-stack ERP-grade inventory and procurement system built with Python and Flask.*

[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?style=for-the-badge&logo=postgresql)](https://postgresql.org)
[![Deploy](https://img.shields.io/badge/Deploy-Render.com-46E3B7?style=for-the-badge)](https://render.com)

---

## 🔗 Live Links

| Page | URL |
|---|---|
| 🌐 **Live App** | *(deploy to Render — see instructions below)* |
| 🐙 **GitHub Repo** | [github.com/tshepisofrominnostation/sipms](https://github.com/tshepisofrominnostation/sipms) |

---

## ✨ Features

| Module | What it does |
|---|---|
| 📊 **Dashboard** | KPI cards, low stock alerts, recent movements, PO status, category value breakdown |
| 📦 **Products** | Full CRUD — add, edit, delete products. Search + category filter. Low stock highlighted |
| 🚛 **Suppliers** | Manage supplier contacts, view their purchase history and linked products |
| 🧾 **Purchase Orders** | Create multi-line POs, approve them, receive stock (auto-updates inventory) |
| 🔄 **Transactions** | Record and view every stock movement with full audit trail |
| 📈 **Reports** | Inventory valuation, supplier spend, PO history — all exportable as CSV (Power BI ready) |

---

## 🏗️ How it Works (for interviews)

```
Browser  →  Flask Routes (app.py)  →  SQLite / PostgreSQL  →  Jinja2 Templates  →  Browser
```

- **Flask** handles HTTP requests. Each `@app.route()` maps a URL to a Python function.
- **SQLite** (local) / **PostgreSQL** (production) store all data. We switch between them using the `DATABASE_URL` environment variable.
- **Jinja2** templates (`templates/`) render HTML using data returned by route functions.
- **Bootstrap 5** handles the responsive UI — no custom CSS framework needed.
- **Gunicorn** runs the app in production (Render.com). Flask's built-in server is dev-only.

---

## 📁 Project Structure

```
sipms/
├── app.py                     # Main Flask app — all routes and database logic
├── wsgi.py                    # Gunicorn entry point for Render.com
├── requirements.txt           # Python dependencies
├── render.yaml                # Render.com deployment config (IaC)
├── Procfile                   # Alternative process config
├── templates/
│   ├── base.html              # Shared layout — sidebar, topbar, flash messages
│   ├── dashboard.html         # Home — KPI overview
│   ├── products.html          # Product catalogue with search/filter
│   ├── suppliers.html         # Supplier management
│   ├── supplier_history.html  # Single supplier detail + PO history
│   ├── purchase_orders.html   # PO creation + approval workflow
│   ├── transactions.html      # Stock movement audit trail
│   └── reports.html           # Analytics + CSV export
└── README.md
```

---

## 🗄️ Database Schema

5 tables — designed to be simple and interview-explainable:

```
suppliers          ← who we buy from
    ↓
products           ← what we stock (linked to supplier)
    ↓           ↘
purchase_orders    po_items          ← PO header + line items
    ↓
inventory_transactions               ← every stock movement (audit log)
```

**Key design decisions:**
- `LEFT JOIN` on products→suppliers so products without a supplier still appear
- `WHERE 1=1` trick in product search so we can safely append AND clauses
- Parameterised queries everywhere (`?` / `%s`) — prevents SQL injection
- `try/except/rollback` on all writes — if anything fails, DB stays clean
- `COALESCE(SUM(...), 0)` on aggregates — avoids NULL in financial totals

---

## 🚀 Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/tshepisofrominnostation/sipms.git
cd sipms

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app (SQLite used automatically in dev)
python app.py

# 4. Open http://localhost:5000
```

Demo data is seeded automatically on first run — 3 suppliers, 8 products, 4 POs, 7 transactions.

---

## ☁️ Deploy to Render.com

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render reads `render.yaml` automatically
4. Click **Apply** — Render will:
   - Create a free PostgreSQL database
   - Install dependencies (`pip install -r requirements.txt`)
   - Start the app with Gunicorn (`gunicorn wsgi:app`)
   - Set `DATABASE_URL` and `SECRET_KEY` automatically

The app detects `DATABASE_URL` at startup and switches from SQLite to PostgreSQL — no code changes needed.

---

## 💡 Things to explain in interviews

**"Why Flask over Django?"**
> Flask is a micro-framework — it gives you just what you need (routing, templating, request handling) without enforcing a project structure. Django is batteries-included and better for large teams. For a focused tool like SIPMS, Flask is faster to ship and easier to reason about.

**"How do you prevent SQL injection?"**
> All user input goes through parameterised queries — I never concatenate strings into SQL. Flask passes parameters as a separate tuple: `execute('SELECT ... WHERE id = ?', (pid,))`. The database driver handles escaping.

**"Why switch from SQLite to PostgreSQL?"**
> SQLite is a file — it's perfect for local dev (zero setup), but it doesn't support concurrent writes well and Render's filesystem resets on each deploy. PostgreSQL is a proper client-server database that handles multiple simultaneous connections and persists data reliably.

**"What is Gunicorn?"**
> Flask's built-in `app.run()` is single-threaded — it handles one request at a time. Gunicorn spawns multiple worker processes so the app can handle concurrent users. It's the standard WSGI server for Python apps in production.

---

## 👤 About

**Developer:** Tshepiso Freddy Thosago
**Company:** Rem0Beg Solutions
**Version:** 1.1 — June 2026
