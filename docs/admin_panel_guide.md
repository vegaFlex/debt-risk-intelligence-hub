# Debt & Risk Intelligence Hub - Admin Panel Guide

This guide explains how to use the Django admin panel in Debt & Risk Intelligence Hub, what each admin section is for, and how to test it safely.

Admin URL:
- https://debt-risk-intelligence-hub.onrender.com/admin/

Important:
- admin access is private and intended for controlled demos only
- do not use the admin panel with the public `visitor_demo` account
- make changes carefully because admin actions can modify live demo data

---

## 1. What the Admin Panel Is For

The admin panel is the operations and control layer of the product.

Use it to:
- review and manage portfolios and debtors
- inspect payments, calls, and promise-to-pay records
- manage user roles and access
- review generated report history
- inspect valuation outputs, benchmarks, and prediction logs
- inspect strategy recommendations, queue assignments, simulator outputs, and action rules

In this project, the admin panel acts as:
- an operations workspace
- a controlled back-office tool
- a data inspection and correction layer

---

## 2. Before You Start

Recommended approach:
- first review the public app UI
- only then enter admin for controlled checks
- avoid random edits in live unless you intentionally want to change demo content

Safe admin usage order:
1. review existing data
2. search and filter records
3. open a record and inspect fields
4. only then create or edit records if needed

---

## 3. Main Admin Sections

The admin panel currently includes these core sections.

### Portfolio domain
- `Portfolios`
- `Debtors`
- `Payments`
- `Call logs`
- `Promises to pay`
- `Data import logs`

### Reporting domain
- `Generated reports`

### Users domain
- `Users`

### Valuation domain
- `Creditors`
- `Portfolio upload batches`
- `Portfolio valuations`
- `Historical benchmarks`
- `Model prediction logs`

### Strategy domain
- `Action rules`
- `Debtor action recommendations`
- `Action scenarios`
- `Strategy runs`
- `Strategy run results`
- `Collector queue assignments`

These records together let you inspect recommendation logic, compare alternative actions, and trace saved strategy runs back to portfolio-level simulations.

---

## 4. Portfolio Domain - What Each Section Does

### 4.1 Portfolios

Purpose:
- each row represents a purchased or imported debt package

Use it for:
- checking source company
- reviewing purchase date
- reviewing purchase price and face value
- confirming currency and dataset context

What to look at:
- portfolio name
- source company
- purchase date
- purchase price
- face value
- created timestamp

Useful admin actions:
- search by portfolio name or source company
- filter by purchase date or currency

When to use it:
- after imports
- when comparing packages
- when validating dashboard/report numbers

### 4.2 Debtors

Purpose:
- debtor-level operational review

Use it for:
- checking debtor profile data
- verifying status, DPD, outstanding amount, and risk score
- investigating why a portfolio looks risky or valuable

What to look at:
- debtor full name
- portfolio
- status
- days past due
- outstanding total
- risk score
- risk band

Useful admin actions:
- search by name, external ID, national ID, phone, email
- filter by status, risk band, region

When to use it:
- after imports
- when validating scoring logic
- when investigating dashboard or valuation outliers

### 4.3 Payments

Purpose:
- confirmed or recorded debtor payments

Use it for:
- checking recovery activity
- validating payment dates and channels
- confirming whether recovery-related metrics make sense

What to look at:
- debtor
- paid amount
- payment date
- channel
- confirmation status

When to use it:
- when recovery rate looks suspicious
- when validating report outputs

### 4.4 Call Logs

Purpose:
- operational call-center activity history

Use it for:
- checking contact behavior
- validating call outcomes and durations
- understanding contact-rate driven performance

What to look at:
- debtor
- agent
- call datetime
- outcome
- duration seconds

When to use it:
- when checking contact rate logic
- when explaining operational effectiveness

### 4.5 Promises to Pay

Purpose:
- expected future payments from debtors

Use it for:
- validating PTP rate and follow-up quality
- checking whether promises were fulfilled

What to look at:
- debtor
- promised amount
- due date
- status
- fulfilled payment

When to use it:
- when the PTP KPI seems high or low
- when comparing package recovery discipline

### 4.6 Data Import Logs

Purpose:
- audit trail for portfolio imports

Use it for:
- checking whether an import succeeded or failed
- reviewing row counts
- confirming imported row volume

What to look at:
- source file name
- file type
- status
- total rows
- valid rows
- imported rows
- created timestamp

When to use it:
- after every import test
- when validating import reliability

---

## 5. Reporting Domain

### 5.1 Generated Reports

Purpose:
- audit and traceability for report generation

Use it for:
- reviewing generated Excel/PDF outputs
- checking report status
- reviewing time period and file metadata

What to look at:
- report type
- report format
- status
- period start / end
- file name
- created timestamp

When to use it:
- after generating management reports
- when validating export availability and consistency

---

## 6. Users and Access Control

### 6.1 Users

Purpose:
- user and role management

Use it for:
- checking who has visitor, analyst, manager, or admin access
- validating role-based access behavior
- reviewing staff/superuser flags

What to look at:
- username
- email
- first name / last name
- role
- is_staff
- is_superuser
- is_active

Role meaning at a high level:
- `visitor` -> public read-only review account
- `analyst` -> restricted API-oriented role
- `manager` -> business operator with more workflow access
- `admin` -> full control including Django admin

When to use it:
- when testing access rules
- when confirming demo account permissions

Safety note:
- be careful when editing roles in live demo data
- changing a role can immediately change what a user can access

---

## 7. Valuation Domain

### 7.1 Creditors

Purpose:
- store creditor context for valuation and benchmark logic

Use it for:
- classifying portfolio origin
- supporting benchmark-aware valuation behavior

What to look at:
- creditor name
- category
- country
- creation timestamp

When to use it:
- before or after valuation imports
- when adjusting benchmark context

### 7.2 Portfolio Upload Batches

Purpose:
- track valuation import batches

Use it for:
- checking which source file created which portfolio valuation intake
- confirming reporting currency and source file metadata

What to look at:
- batch name
- creditor
- linked portfolio
- reporting currency
- source file name
- created timestamp

When to use it:
- after valuation import tests
- when tracing acquisition intake history

### 7.3 Portfolio Valuations

Purpose:
- stored valuation results for acquisition review

Use it for:
- reviewing saved expected recovery
- reviewing recommended bid and projected ROI
- checking which method was used
- inspecting valuation factors inline

What to look at:
- portfolio
- valuation method
- expected recovery rate
- recommended bid percent
- recommended bid amount
- projected ROI
- confidence score
- created timestamp

Special note:
- valuation factors appear inline on the valuation record
- this is useful for explanation and traceability

When to use it:
- after running and saving valuations
- when comparing historical valuation runs

### 7.4 Historical Benchmarks

Purpose:
- benchmark assumptions for hybrid valuation logic

Use it for:
- reviewing or adjusting benchmark inputs
- supporting creditor/category fallback behavior
- supporting similarity-based valuation fallback

What to look at:
- creditor
- creditor category
- product type
- DPD band
- balance band
- average recovery rate
- sample size
- region

When to use it:
- when explaining benchmark-based pricing
- when fine-tuning valuation assumptions

Safety note:
- editing benchmarks can change valuation behavior across multiple packages
- use carefully in live demo data

### 7.5 Model Prediction Logs

Purpose:
- log the ML baseline outputs used during valuation review

Use it for:
- checking prediction type
- checking prediction value and confidence
- reviewing model version

What to look at:
- portfolio
- prediction type
- prediction value
- confidence
- model version
- created timestamp

When to use it:
- after valuation save actions
- when explaining ML baseline output in the product

## 8. Strategy Domain

### 8.1 Action Rules

Purpose:
- store the rules used by the collections strategy engine

Use it for:
- reviewing which debtor conditions map to which actions
- validating recommended action, channel, uplift, and priority weights
- checking whether a recent rule change explains strategy output differences

What to look at:
- rule name
- risk band
- debtor status
- DPD range
- required contact fields
- recommended action
- recommended channel
- base uplift
- priority weight
- active flag

### 8.2 Debtor Action Recommendations

Purpose:
- stored recommendation output for debtor-level next-best-action review

Use it for:
- checking what action was recommended
- reviewing priority score and expected uplift
- validating reason summaries against debtor context

What to look at:
- debtor
- recommended action
- recommended channel
- priority score
- expected uplift percent
- expected uplift amount
- reason summary
- created timestamp

### 8.3 Action Scenarios

Purpose:
- scenario-level comparison records for debtor actions

Use it for:
- checking the expected recovery and uplift for different actions
- validating estimated cost and ROI assumptions

### 8.4 Strategy Runs

Purpose:
- parent records for saved strategy simulations

Use it for:
- reviewing when a strategy comparison was executed
- tracing which portfolio and strategy set was evaluated
- confirming who saved the run and when

What to look at:
- strategy name
- portfolio
- strategy type
- created by
- created timestamp

### 8.5 Strategy Run Results

Purpose:
- stored summary outcomes for each strategy run

Use it for:
- comparing expected total recovery
- reviewing expected uplift, cost, and ROI
- validating the winning strategy narrative

What to look at:
- linked strategy run
- debtor count
- expected total recovery
- expected total uplift
- expected cost
- expected ROI
- notes

### 8.6 Collector Queue Assignments

Purpose:
- operational queue records for prioritized debtor assignments

Use it for:
- checking who or which lane owns a case
- validating queue rank and recommended action
- confirming whether queue grouping looks sensible

---

## 9. How to Work in the Admin Panel Safely

Use this sequence.

### Safe review workflow
1. Open `/admin/`
2. Start with `Portfolios`
3. Open the package you want to inspect
4. Move to `Debtors` for detailed case review
5. Check `Payments`, `Call logs`, and `Promises to pay` if KPI explanations are needed
6. Check `Generated reports` if a report/export was recently created
7. Check `Portfolio valuations` and `Historical benchmarks` for acquisition review logic
8. Check `Action rules`, `Debtor action recommendations`, `Strategy runs`, `Strategy run results`, and `Collector queue assignments` for collections strategy logic

### When editing data
Before editing anything, ask:
- do I need this change for a test?
- will this alter live demo outputs?
- do I need to capture the original state first?

Best practice:
- prefer reviewing over editing
- make small changes only
- if you edit, note what changed so you can verify the effect in the app UI

---

## 10. Step-by-Step Admin Testing Checklist

### 10.1 Admin login
1. Open `/admin/`
2. Sign in with private admin credentials
3. Expected result:
- branded admin loads
- only authorized admin can enter

### 10.2 Portfolio review
1. Open `Portfolios`
2. Search for a known portfolio
3. Open the record
4. Expected result:
- key commercial fields are visible and correct

### 10.3 Debtor review
1. Open `Debtors`
2. Filter by `risk_band`
3. Search for a debtor by name
4. Open the debtor
5. Expected result:
- status, DPD, outstanding total, risk score, and risk band are visible

### 10.4 Import audit trail
1. Open `Data import logs`
2. Review the latest import row
3. Expected result:
- file name, status, and row counts look correct

### 10.5 Report log review
1. Open `Generated reports`
2. Review recent records
3. Expected result:
- generated outputs are logged with type, format, status, and file name

### 10.6 User role review
1. Open `Users`
2. Inspect `visitor_demo`
3. Inspect `analyst_demo`
4. Expected result:
- each account has the correct role and flags

### 10.7 Valuation history review
1. Open `Portfolio valuations`
2. Open a stored valuation
3. Review inline `Valuation factors`
4. Expected result:
- saved pricing output and explanatory factors are visible

### 10.8 Benchmark review
1. Open `Historical benchmarks`
2. Filter by category or region
3. Expected result:
- benchmark rows are searchable and understandable

### 10.9 Prediction log review
1. Open `Model prediction logs`
2. Review recent prediction entries
3. Expected result:
- prediction type, value, confidence, and model version are visible

### 10.10 Strategy rule review
1. Open `Action rules`
2. Review an existing rule
3. Expected result:
- DPD range, action, channel, uplift, and active state are visible

### 10.11 Strategy recommendation review
1. Open `Debtor action recommendations`
2. Review a recent recommendation
3. Expected result:
- debtor, action, channel, priority score, and reason summary are visible

### 10.12 Queue assignment review
1. Open `Collector queue assignments`
2. Review top-ranked records
3. Expected result:
- queue rank, action type, and collector assignment are visible

### 10.13 Strategy run history review
1. Open `Strategy runs`
2. Open a recent saved run
3. Open `Strategy run results`
4. Expected result:
- saved run points to the correct portfolio and strategy type
- run results show recovery, uplift, cost, and ROI summaries

---

## 11. What You Can Do from Admin

You can use admin to:
- inspect portfolios and debtors in detail
- search operational and valuation records quickly
- review imports and generated reports
- validate role assignments
- inspect valuation history and model logs
- inspect strategy rules, recommendations, scenario outputs, saved run history, and queue assignments
- manage benchmark assumptions
- make controlled corrections to live demo data

What admin is especially good for:
- traceability
- operational audits
- debugging inconsistent outputs
- demoing back-office capability

---

## 12. What You Should Avoid in Live Admin

Avoid:
- random deletion of portfolios or debtors
- changing user roles without purpose
- editing benchmarks casually
- creating noisy test data without noting it
- making multiple edits without checking the public UI impact

Reason:
- admin changes can affect dashboard, reports, valuation outputs, and demo screenshots

---

## 13. Best Demo Flow with Admin

If you present the product to someone and want to use admin as part of the story, the best order is:

1. show dashboard
2. show report preview
3. show valuation workspace
4. show strategy workspace or collector queue
5. then show admin panel as the controlled back-office layer

This works well because:
- first you show business-facing output
- then you show operational control and traceability

---

## 14. Quick Reference

### Best sections for business review
- `Portfolios`
- `Debtors`
- `Generated reports`
- `Portfolio valuations`
- `Historical benchmarks`
- `Action rules`
- `Collector queue assignments`

### Best sections for access control testing
- `Users`

### Best sections for import/export traceability
- `Data import logs`
- `Generated reports`
- `Portfolio upload batches`

---

## 15. Admin Testing Notes Template

```text
Admin Section:
Record / Filter Used:
Expected Result:
Actual Result:
Pass / Fail:
Notes:
```

---

## 16. Final Guidance

Think of the admin panel as:
- the product's control room
- the inspection layer behind the user-facing analytics UI
- the safest place to verify data relationships and generated outputs

Use it carefully, and it becomes one of the strongest parts of the whole application.
