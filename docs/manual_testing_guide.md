# Debt & Risk Intelligence Hub - Manual Testing Guide

This guide is designed for full manual QA of the live application at:
- https://debt-risk-intelligence-hub.onrender.com/

It is written as a practical step-by-step checklist so you can test the product screen by screen, role by role, and flow by flow.

---

## 1. Testing Goal

Use this guide to verify:
- access control and role behavior
- portfolio analytics and filtering
- debtor review workflows
- reporting and export restrictions
- valuation and acquisition review workflows
- benchmark and comparison screens
- API availability
- documentation pages
- anonymous user restrictions

---

## 2. Test Accounts

### Public review account
- Username: `visitor_demo`
- Password: `DemoPass123!`

Purpose:
- read-only walkthrough account for recruiters, clients, and public reviewers

Expected behavior:
- can view dashboards, reports preview, valuation workspace, comparison desk, benchmark library, and docs
- cannot import data, export reports, save valuations, edit benchmarks, or access admin

### Restricted API account
- Username: `analyst_demo`
- Password: `DemoPass123!`

Purpose:
- restricted analyst access test

Expected behavior:
- can access selected API endpoints
- cannot access dashboard/reports/valuation management screens

### Private admin account
Purpose:
- controlled full-access review

Expected behavior:
- full access including `/admin/`, imports, exports, valuation save actions, and benchmark editing

Note:
- private admin credentials are intentionally not listed here

---

## 3. Pre-Test Notes

Before testing the live demo:
- the Render free instance may take 20-30 seconds to wake up on first load
- use `Ctrl+F5` if an old page seems cached
- if `visitor_demo` is missing after a redeploy, the environment may need temporary reseeding

Recommended browser setup:
- one normal window for logged-in review
- one incognito/private window for anonymous access tests

---

## 4. Core URLs

### Main application
- Home / root: `https://debt-risk-intelligence-hub.onrender.com/`
- Login: `https://debt-risk-intelligence-hub.onrender.com/accounts/login/`
- Dashboard: `https://debt-risk-intelligence-hub.onrender.com/dashboard/`
- Full Debtor List: `https://debt-risk-intelligence-hub.onrender.com/dashboard/debtors/`
- Report Preview: `https://debt-risk-intelligence-hub.onrender.com/reports/management/`
- Portfolio Import: `https://debt-risk-intelligence-hub.onrender.com/portfolio/import/`

### Valuation layer
- Valuation Workspace: `https://debt-risk-intelligence-hub.onrender.com/valuation/`
- Comparison Desk: `https://debt-risk-intelligence-hub.onrender.com/valuation/compare/`
- Benchmark Library: `https://debt-risk-intelligence-hub.onrender.com/valuation/benchmarks/`
- Valuation Import: `https://debt-risk-intelligence-hub.onrender.com/valuation/import/`

### Documentation
- User Guide: `https://debt-risk-intelligence-hub.onrender.com/docs/user-guide/`
- Buyer Guide: `https://debt-risk-intelligence-hub.onrender.com/docs/buyer-guide/`
- Buyer One-Pager: `https://debt-risk-intelligence-hub.onrender.com/docs/buyer-one-pager/`

### API
- Portfolios API: `https://debt-risk-intelligence-hub.onrender.com/api/portfolios/`
- Debtors API: `https://debt-risk-intelligence-hub.onrender.com/api/debtors/`
- KPI Overview API: `https://debt-risk-intelligence-hub.onrender.com/api/kpis/overview/`

---

## 5. Anonymous User Tests

Use an incognito/private window.

### 5.1 Root behavior
1. Open `/`
2. Confirm the app redirects to a login-protected flow
3. Expected result:
- no privileged content should be editable
- public docs may still be reachable directly

### 5.2 Login page
1. Open `/accounts/login/`
2. Expected result:
- clean login screen
- no demo credentials printed directly on the page
- no admin credential hints

### 5.3 Portfolio import must be closed
1. Open `/portfolio/import/`
2. Expected result:
- anonymous user is redirected to login
- import form must not remain publicly usable

### 5.4 Valuation import must be closed
1. Open `/valuation/import/`
2. Expected result:
- anonymous user is redirected to login

### 5.5 Admin must be closed
1. Open `/admin/`
2. Expected result:
- login required
- no anonymous admin access

### 5.6 Public documentation pages
1. Open `/docs/user-guide/`
2. Open `/docs/buyer-guide/`
3. Open `/docs/buyer-one-pager/`
4. Expected result:
- pages render in browser
- they do not show source code view
- content is readable and styled as documentation pages

---

## 6. Visitor Demo Tests

Log in with:
- `visitor_demo / DemoPass123!`

The goal here is to confirm that the public review account can see the important product screens but cannot change data.

### 6.1 Login and header
1. Sign in as `visitor_demo`
2. Expected result:
- top-right user pill shows `visitor_demo`
- nav shows the user-facing product sections
- no admin access should appear

### 6.2 Dashboard overview
1. Open `/dashboard/`
2. Expected result:
- KPI cards load
- filters are visible
- charts render
- numbers use compact formatting where appropriate, e.g. `1.36M`

### 6.3 Dashboard filtering
1. Change `Portfolio`
2. Change `Risk Band`
3. Change `Status`
4. Click `Apply Filters`
5. Expected result:
- KPI values update
- chart blocks update
- debtor match count changes

### 6.4 Reset filters
1. Click `Reset`
2. Expected result:
- filters return to default state
- dashboard shows full dataset again

### 6.5 Full Debtor List
1. Open `Full Debtor List`
2. Expected result:
- table loads with debtors
- sorting and pagination work
- visitor can review but not perform admin-only changes

### 6.6 Reports preview
1. Open `/reports/management/`
2. Expected result:
- report preview loads
- KPI cards load
- compact monetary formatting is used where expected
- visitor can read the report preview

### 6.7 Report exports must be blocked for visitor
1. Try to find Excel/PDF export actions
2. If you can reach export URLs directly, open them
3. Expected result:
- visitor should not be allowed to export
- system should show a friendly restricted message or deny access safely

### 6.8 Valuation workspace
1. Open `/valuation/`
2. Expected result:
- ranking KPI cards load
- `Attractiveness` and `Confidence` are clearly shown as scores
- filters and sorting controls are visible
- `Portfolio Comparison Desk` callout is visible

### 6.9 Valuation filters and sorting
1. Change `Signal`
2. Change `Recommendation`
3. Change `Mode`
4. Change `Sort By`
5. Click `Apply Review Filters`
6. Expected result:
- ranked results update correctly
- empty state should be clean if no records match

### 6.10 Open valuation preview
1. From the valuation workspace, open a portfolio preview
2. Expected result:
- recommendation block is visible
- KPI cards show expected recovery, collections, bid, ROI, and confidence
- scenario analysis table is visible
- ML baseline forecast section is visible
- historical saved valuation section can be reviewed if available

### 6.11 Visitor must not save valuations
1. Try to find `Run and Save Valuation`
2. If you can hit a save action URL directly, try it
3. Expected result:
- visitor must not be allowed to save valuations
- friendly restricted message should appear

### 6.12 Comparison desk
1. Open `/valuation/compare/`
2. Select 2 or 3 portfolios
3. Expected result:
- side-by-side comparison loads
- KPI comparison, recommendation, and delta sections are readable
- compact money formatting is preserved

### 6.13 Comparison selection warning
1. Select more than 3 portfolios if the UI allows it
2. Expected result:
- clear warning explains the comparison limit
- no broken layout or confusing behavior

### 6.14 Benchmark library
1. Open `/valuation/benchmarks/`
2. Expected result:
- visitor can review benchmark rows
- page should read as read-only for visitor
- visitor must not be able to edit or create benchmark records

### 6.15 Valuation import must be blocked for visitor
1. Open `/valuation/import/`
2. Expected result:
- visitor receives a friendly restriction message
- import form must not be usable

### 6.16 Portfolio import must be blocked for visitor
1. Open `/portfolio/import/`
2. Expected result:
- visitor receives a friendly restriction message
- import form must not be usable

### 6.17 Documentation menu
1. Open the `Documentation` dropdown from the app header
2. Expected result:
- it should link to `User Guide`
- buyer-facing materials should not clutter the main app nav

### 6.18 More Actions dropdown
1. Open `More Actions`
2. Expected result:
- dropdown indicator is visible
- entries are readable and role-appropriate
- no admin-only action should appear for visitor

---

## 7. Analyst Demo Tests

Log in with:
- `analyst_demo / DemoPass123!`

The goal here is to verify that the analyst role is restricted as designed.

### 7.1 Dashboard restriction
1. Open `/dashboard/`
2. Expected result:
- analyst should receive a friendly access restriction screen
- messaging should explain that access is limited

### 7.2 Reports restriction
1. Open `/reports/management/`
2. Expected result:
- analyst should not have management report access
- friendly restricted page should appear

### 7.3 KPI API restriction
1. Open `/api/kpis/overview/`
2. Expected result:
- analyst should not receive the full KPI overview if restricted by policy

### 7.4 API access that should work
1. Open `/api/portfolios/`
2. Open `/api/debtors/`
3. Expected result:
- analyst can access the allowed API endpoints
- responses render normally

---

## 8. Private Admin / Full Access Tests

Run these only when you have private admin credentials.

### 8.1 Admin panel
1. Log in with the private admin account
2. Open `/admin/`
3. Expected result:
- admin dashboard loads
- portfolios, debtors, users, reports, and valuation-related records are manageable

### 8.2 Portfolio import flow
1. Open `/portfolio/import/`
2. Upload a valid portfolio file
3. Click `Validate & Preview`
4. Review the preview
5. Save the import
6. Expected result:
- validation works
- preview appears before save
- persisted portfolio becomes available in dashboard/debtor/report views

### 8.3 Import validation errors
1. Upload an invalid file
2. Expected result:
- clear validation errors appear
- data is not saved

### 8.4 Report exports
1. Open `/reports/management/`
2. Export Excel
3. Export PDF
4. Expected result:
- files download successfully
- report formatting is readable
- exported values match the preview

### 8.5 Valuation import
1. Open `/valuation/import/`
2. Upload a valuation intake file
3. Validate preview
4. Create portfolio and open valuation
5. Expected result:
- acquisition intake flow works end to end
- new portfolio is available in valuation workspace

### 8.6 Run and save valuation
1. Open a valuation preview
2. Run and save valuation
3. Expected result:
- saved valuation history updates
- new run is visible in historical comparison
- prediction logs are created

### 8.7 Benchmark editing
1. Open `/valuation/benchmarks/`
2. Create or edit a benchmark record
3. Expected result:
- benchmark changes save correctly
- valuation logic can use benchmark fallback without errors

---

## 9. API Manual Checks

### 9.1 Portfolios API
Open:
- `/api/portfolios/`

Check:
- response is valid
- portfolio list is readable
- fields look consistent

### 9.2 Debtors API
Open:
- `/api/debtors/`

Check:
- debtor rows are returned
- filtering and ordering behave correctly where supported

Suggested examples:
- `/api/debtors/?risk_band=high`
- `/api/debtors/?ordering=-outstanding_total`
- `/api/debtors/?search=Petrov`

### 9.3 KPI overview API
Open:
- `/api/kpis/overview/`

Check:
- manager/admin should receive KPI payload
- analyst restrictions should still hold if applicable

---

## 10. Documentation Checks

### 10.1 User Guide
Open `/docs/user-guide/`

Check:
- page opens in browser
- content explains product usage clearly
- no raw markdown/source leakage in the UI

### 10.2 Buyer Guide
Open `/docs/buyer-guide/`

Check:
- page reads like a presentation guide
- sections are business-oriented
- suitable for browser review or PDF export

### 10.3 Buyer One-Pager
Open `/docs/buyer-one-pager/`

Check:
- page is concise
- suitable for quick sharing
- formatting is print-friendly

---

## 11. UI and UX Review Checklist

Use this section as a design/usability pass.

Check:
- dropdown buttons show a clear indicator that they expand
- dashboard navigation is logically grouped
- `Valuation` is visible in the main left-side product navigation
- `Documentation` is in the right-side helper/admin group
- compact number formatting is used for large money values
- score-based metrics clearly indicate they are scores, not percentages
- callouts and action blocks do not have broken spacing or excessive white space
- restricted pages use friendly messaging instead of raw 403 errors

---

## 12. Security and Access Regression Checklist

Check the following after any important change:
- anonymous users cannot use import screens
- login screen does not print demo credentials
- public `visitor_demo` is read-only
- analyst cannot access manager/admin screens
- admin credentials are not exposed in README, docs, or login page
- documentation pages open safely without exposing source code or secrets

---

## 13. Suggested Full Testing Order

If you want the cleanest full pass, use this order:

1. Anonymous access tests
2. `visitor_demo` walkthrough
3. `analyst_demo` restriction checks
4. API checks
5. Documentation checks
6. Private admin full-access tests
7. Final UI/UX regression pass
8. Final security regression pass

---

## 14. Test Notes Template

Use this template while testing:

```text
Screen / Flow:
Account Used:
URL:
Expected Result:
Actual Result:
Pass / Fail:
Notes:
```

---

## 15. Exit Criteria

The application is in a good testing state if:
- all public review flows work with `visitor_demo`
- restricted actions are blocked cleanly
- analytics and valuation screens render correctly
- documentation pages are reachable and readable
- no anonymous import/admin access remains
- exports and write actions work only for authorized roles

---

## 16. Related Documentation

- User Guide: `/docs/user-guide/`
- Buyer Guide: `/docs/buyer-guide/`
- Buyer One-Pager: `/docs/buyer-one-pager/`
- Demo Checklist: `docs/demo_checklist.md`

