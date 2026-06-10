# SIPMS — Smart Inventory & Procurement Management System

**Developed by Tshepiso Freddy Thosago | Rem0Beg Solutions**

A full-stack ERP-grade inventory and procurement management system built with Python, Flask, and SQLite.

## Features

- **Dashboard** — KPI cards, low stock alerts, PO status summary, category breakdown, recent transactions
- **Products** — Full CRUD with search, category filter, cost/selling price, reorder levels
- **Suppliers** — Supplier management with purchase history and product linkage  
- **Purchase Orders** — Create, approve, close POs with automatic stock receipt and inventory update
- **Inventory Transactions** — Receive, issue, and adjust stock with full audit trail
- **Reports** — Inventory, supplier spend, and PO reports with CSV export (Power BI ready)

## Tech Stack

- **Backend:** Python 3.11, Flask 3.0
- **Database:** SQLite (upgradeable to MySQL/PostgreSQL)
- **Frontend:** HTML5, CSS3, Vanilla JS
- **Hosting:** Render.com
- **Version Control:** GitHub

## Local Setup

```bash
pip install -r requirements.txt
python wsgi.py
```

Open http://localhost:5000

## Deploy to Render

1. Push to GitHub
2. Connect repo on render.com
3. Set start command: `gunicorn wsgi:app`
4. Deploy

---

*Built as a portfolio project aligned to ERP and supply chain management principles.*
