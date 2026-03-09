# Debt & Risk Intelligence Hub

MVP platform for debt portfolio analysis, risk scoring, call center KPI tracking, and management reporting.

## Modules
- users
- portfolio
- scoring
- reports
- dashboard

## Tech Stack
- Python 3.13
- Django + Django REST Framework
- SQLite (local dev)
- openpyxl (Excel exports)
- reportlab (PDF exports)

## Quick Start (Local)
1. `python -m venv .venv`
2. `.\.venv\Scripts\Activate.ps1`
3. `pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py seed_demo_data`
6. `python manage.py runserver`

## Demo Accounts
- `manager_demo / DemoPass123!`
- `analyst_demo / DemoPass123!`
- `admin_demo / DemoPass123!`

## Main URLs
- Dashboard: `http://127.0.0.1:8000/dashboard/`
- Data import: `http://127.0.0.1:8000/portfolio/import/`
- API portfolios: `http://127.0.0.1:8000/api/portfolios/`
- API debtors: `http://127.0.0.1:8000/api/debtors/`
- API KPI overview: `http://127.0.0.1:8000/api/kpis/overview/`

## Reports
- Excel export: `/reports/management/excel/`
- PDF export: `/reports/management/pdf/`
- Weekly command: `python manage.py generate_weekly_reports`

## Role Access
- Analyst: portfolio/debtor APIs
- Manager: dashboard, KPI API, report exports
- Admin: full manager access + admin privileges

## Local Demo Walkthrough
See: `docs/demo_checklist.md`
