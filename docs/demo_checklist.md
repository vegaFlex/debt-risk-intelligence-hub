# Demo Checklist (Localhost)

## 1) Setup

1. `python -m venv .venv`
2. `\.venv\Scripts\Activate.ps1`
3. `pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py seed_demo_data`
6. `python manage.py runserver`

## 2) Login credentials

- Visitor: `visitor_demo / DemoPass123!`
- Analyst: `analyst_demo / DemoPass123!`
- Private admin / manager access: controlled demo only

## 3) Functional checks

1. Open `http://127.0.0.1:8000/dashboard/`
2. Login as `visitor_demo` and verify:
- KPI cards are visible
- Performance block is visible
- Top risk debtors table is populated
- Top risk segments table is populated
- report preview is visible
- valuation workspace is visible
- export and save actions are hidden or restricted

3. Open `http://127.0.0.1:8000/valuation/`
- ranking workspace loads
- comparison desk opens
- benchmark library opens in read-only mode

4. Open `http://127.0.0.1:8000/reports/management/`
- preview loads
- export buttons are hidden for visitor

5. API checks (while logged in):
- `http://127.0.0.1:8000/api/portfolios/`
- `http://127.0.0.1:8000/api/debtors/`

## 4) Role checks

1. Login as `analyst_demo`
- `/api/portfolios/` should work
- `/api/debtors/` should work
- `/dashboard/` should show a friendly restricted message

2. Login as a controlled manager/admin account
- `/dashboard/` should work
- `/reports/management/excel/` should work
- `/reports/management/pdf/` should work
- `/valuation/import/` should work
- `/valuation/benchmarks/` should allow editing
