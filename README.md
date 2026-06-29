# 📦 SIPMS — Smart Inventory & Procurement Management System

> *Track stock. Manage suppliers. Control procurement. All in one place.*

**Built by Tshepiso Freddy Thosago | Rem0Beg Solutions**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql)](https://postgresql.org)
[![Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?style=for-the-badge&logo=railway)](https://railway.app)

---

## 🌐 Live Demo

**👉 [https://sipms-production.up.railway.app](https://sipms-production.up.railway.app)**

---

## 💡 What SIPMS Solves

Small-to-medium businesses and schools struggle with:
- Stock going missing with no paper trail
- Manual purchase order processes on spreadsheets
- No visibility of supplier performance or pricing history
- Zero alerts when stock drops below reorder levels

SIPMS solves this with a web-based system that tracks every product, every supplier, every purchase order, and every transaction — with CSV export for accountants.

---

## ✨ Features

| Module | What it does |
|---|---|
| 📦 **Products** | Add/edit products, set reorder levels, track stock quantity |
| 🏭 **Suppliers** | Supplier profiles, contact info, order history |
| 🛒 **Purchase Orders** | Raise POs, approve them, auto-update stock on receipt |
| 📊 **Dashboard** | Low stock alerts, pending POs, spend overview |
| 📜 **Transaction Log** | Every stock movement is recorded with timestamp and user |
| 📤 **CSV Export** | Export any report for Excel/accounting |

---

## 🏗️ Architecture

```
Browser (HTML + Jinja2 templates)
         │
         ▼
Flask Application (app.py)
  - @app.route() decorators handle each URL
  - Jinja2 renders HTML templates with data
  - Flash messages for user feedback
         │
         ▼
get_db() — database abstraction layer
  - SQLite  → local development (file-based, zero config)
  - PostgreSQL → Railway production (DATABASE_URL env var)
         │
         ▼
18 SQL routes across 5 modules
```

**Why this architecture?**
Flask is a "micro-framework" — it gives you routing and templating but you choose everything else. This makes the code easy to read and explain. Every route is a Python function. Every page is a Jinja2 template. No magic.

---

## 🗄️ Database Design

```sql
-- 5 core tables
products        (id, name, sku, quantity, reorder_level, unit_price, supplier_id)
suppliers       (id, name, contact_person, email, phone, address)
purchase_orders (id, supplier_id, status, total_amount, created_at)
po_items        (id, po_id, product_id, quantity, unit_price)
transactions    (id, product_id, type, quantity, notes, created_at)
```

**Key decisions:**
- `reorder_level` on every product — dashboard queries `WHERE quantity < reorder_level` for instant alerts
- `transactions` table is append-only (no deletes) — full audit trail
- `po_items` separate from `purchase_orders` — one PO can have many line items (one-to-many)
- Dual database support via `get_db()` — same codebase runs on SQLite locally and PostgreSQL in production

---

## 🔁 How a Purchase Order Works (Step by Step)

```
1. User raises PO → status = 'PENDING'
2. Manager approves → status = 'APPROVED'
3. Goods received → status = 'RECEIVED'
   → Flask atomically:
      a. Updates each product's quantity (+= po_item.quantity)
      b. Creates a Transaction record for each item
      c. Commits everything — if any step fails, all roll back
```

This is implemented using a single database connection with `conn.commit()` — either all updates succeed or none do.

---

## ⚙️ Local Setup

```bash
git clone https://github.com/tshepisofrominnostation/sipms.git
cd sipms

pip install -r requirements.txt

# Runs on SQLite locally — no database setup needed
python app.py
# Open http://localhost:5000
```

---

## ☁️ Railway Deployment

1. Push to GitHub
2. Railway → New Project → Deploy from GitHub → `sipms`
3. Add PostgreSQL plugin → Railway auto-sets `DATABASE_URL`
4. Add env var: `SECRET_KEY=your-random-string`
5. Railway auto-detects Python via `nixpacks.toml` → deploys

The `DATABASE_URL.replace('postgres://', 'postgresql://', 1)` line fixes a known Railway/psycopg2 URL prefix mismatch.

---

## 💡 Interview Q&A

**"Why Flask over Django?"**
> Flask is a micro-framework — it gives you routing and templating and you add what you need. Django is "batteries included" but that means more to learn and more magic happening behind the scenes. For a portfolio project where I need to explain every line, Flask is better because there's no hidden ORM or admin panel I didn't write myself. I understand everything in this codebase.

**"How does your dual-database setup work?"**
> The `get_db()` function checks for the `DATABASE_URL` environment variable. If it exists (production/Railway), it connects to PostgreSQL using `psycopg2`. If not (local dev), it connects to a SQLite file. The SQL queries are standard enough that they run on both without changes. This is called environment-based configuration — the same code behaves differently depending on where it's running.

**"What is `psycopg2` and why do you need it?"**
> `psycopg2` is the Python driver for PostgreSQL — it's the adapter that lets Python talk to a Postgres database. SQLite is built into Python's standard library, but PostgreSQL is a separate server, so you need a driver. `psycopg2-binary` is the pre-compiled version that installs without needing a C compiler.

**"How do you prevent stock going negative?"**
> Before any stock deduction I check `WHERE quantity >= deduction_amount`. If the stock isn't there, the transaction is rejected with a flash error message. This check and the deduction happen in the same database connection so there's no race condition window.

**"What are Jinja2 templates?"**
> Jinja2 is Flask's templating engine. It lets you write HTML with Python-like syntax — `{{ variable }}` to print a value, `{% for item in items %}` to loop, `{% if condition %}` for conditionals. Flask renders the template server-side and sends plain HTML to the browser. This is called server-side rendering (SSR), as opposed to React which renders client-side.

**"Why an append-only transactions table?"**
> Deleting or updating records hides history. If someone adjusts stock incorrectly, I need to know what happened and when. The transactions table only ever gets INSERT statements — never UPDATE or DELETE. This gives a complete, tamper-proof audit trail. The current stock level is always `SUM(quantity) WHERE type='in'` minus `SUM(quantity) WHERE type='out'` — or I just track it on the product row and use transactions as the log.

---

## 👤 About

**Developer:** Tshepiso Freddy Thosago | Rem0Beg Solutions
**GitHub:** [github.com/tshepisofrominnostation](https://github.com/tshepisofrominnostation)

**Other projects:**
- [Dinoto Technical SS ERP](https://github.com/tshepisofrominnostation/dinoto-school-erp) — School asset & textbook management
- [Rem0Beg Pay](https://github.com/tshepisofrominnostation/rem0beg-pay) — Earned Wage Access platform
- [Book-Smart](https://github.com/tshepisofrominnostation/book-smart) — School inventory management
