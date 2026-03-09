# Demo Checklist (Localhost)

## 1) Setup

1. `python -m venv .venv`
2. `.\.venv\Scripts\Activate.ps1`
3. `pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py seed_demo_data`
6. `python manage.py runserver`

## 2) Login credentials

- Manager: `manager_demo / DemoPass123!`
- Analyst: `analyst_demo / DemoPass123!`
- Admin: `admin_demo / DemoPass123!`

## 3) Functional checks

1. Open `http://127.0.0.1:8000/dashboard/`
2. Login as `manager_demo` and verify:
- KPI cards are visible
- Performance block is visible
- Top risk debtors table is populated
- Top risk segments table is populated

3. Try exports from dashboard:
- Download Excel
- Download PDF

4. Open `http://127.0.0.1:8000/portfolio/import/`
- Upload a valid CSV
- Click `Validate & Preview`
- Click `Confirm Import`

5. API checks (while logged in):
- `http://127.0.0.1:8000/api/portfolios/`
- `http://127.0.0.1:8000/api/debtors/`
- `http://127.0.0.1:8000/api/kpis/overview/`

## 4) RBAC checks

1. Login as `analyst_demo`
- `/api/portfolios/` should work
- `/api/kpis/overview/` should return `403`
- `/dashboard/` should return `403`

2. Login as `manager_demo`
- `/dashboard/` should work
- `/reports/management/excel/` should work
- `/reports/management/pdf/` should work
