# Debt & Risk Intelligence Hub - Admin Cheat Sheet

Quick admin reference for fast review and safe demo use.

Admin URL:
- https://debt-risk-intelligence-hub.onrender.com/admin/

---

## 1. Best First Screens

If you open admin and want the fastest useful review, start here:

1. `Portfolios`
2. `Debtors`
3. `Generated reports`
4. `Portfolio valuations`
5. `Historical benchmarks`
6. `Action rules`
7. `Strategy runs`
8. `Strategy run results`
9. `Collector queue assignments`
10. `Users`

---

## 2. What to Check First

### Portfolios
Use for:
- package name
- source company
- purchase date
- purchase price
- face value

### Debtors
Use for:
- status
- DPD
- outstanding total
- risk score
- risk band

### Generated reports
Use for:
- report history
- export status
- file names
- reporting periods

### Portfolio valuations
Use for:
- expected recovery
- recommended bid
- projected ROI
- confidence score
- valuation factors

### Historical benchmarks
Use for:
- benchmark assumptions
- product type
- DPD band
- balance band
- avg recovery rate

### Action rules
Use for:
- next-best-action rule review
- channel and uplift assumptions
- DPD and contact condition checks

### Strategy runs
Use for:
- saved simulator history
- portfolio-level strategy review
- checking who saved a run and when

### Strategy run results
Use for:
- recovery, uplift, cost, and ROI summary review
- validating the winning strategy snapshot

### Collector queue assignments
Use for:
- queue rank review
- collector/lane allocation
- action priority verification

### Users
Use for:
- role checks
- `visitor_demo`
- `analyst_demo`
- admin/staff flags

---

## 3. Safest Demo Workflow

If you are showing the admin panel to someone:

1. open `Portfolios`
2. open `Debtors`
3. show `Generated reports`
4. show `Portfolio valuations`
5. show `Historical benchmarks`
6. show `Action rules`
7. show `Strategy runs`
8. show `Strategy run results`
9. show `Collector queue assignments`
10. show `Users`

This tells the strongest story:
- commercial portfolio context
- operational debtor detail
- report traceability
- acquisition review logic
- benchmark intelligence
- role-based access control

---

## 4. Best Uses of Admin

Admin is best for:
- verifying data behind the dashboard
- tracing import and report history
- validating role access
- reviewing valuation logic inputs and outputs
- reviewing collections strategy logic, saved run history, and queue outcomes
- controlled correction of demo data

---

## 5. Avoid These in Live Demo

Avoid:
- deleting portfolios
- changing user roles casually
- editing benchmarks randomly
- creating noisy test records without noting them

Reason:
- changes in admin can affect dashboard, reports, and valuation outputs immediately

---

## 6. Quick Role Check

### visitor_demo
Should be:
- read-only public review account
- no import
- no export
- no save actions
- no admin access

### analyst_demo
Should be:
- restricted role
- limited API-oriented access
- no dashboard/report/admin access

### private admin
Should be:
- full admin control
- staff + superuser

---

## 7. Ultra-Short Checklist

```text
[ ] Portfolios look correct
[ ] Debtor risk/status data looks correct
[ ] Reports are logged
[ ] Valuations are stored correctly
[ ] Benchmarks exist and look reasonable
[ ] Strategy rules look reasonable
[ ] Saved strategy runs look reasonable
[ ] Queue assignments look reasonable
[ ] Demo user roles are correct
```

---

## 8. Fastest Admin Story in One Sentence

The admin panel is the product's control room: it lets you inspect portfolios, debtors, reports, roles, valuation logic, and collections strategy records behind the public analytics screens.

