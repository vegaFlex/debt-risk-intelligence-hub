# Debt & Risk Intelligence Hub - User Guide

## 1. Purpose of the Application

Debt & Risk Intelligence Hub is an analytics platform for reviewing debtor portfolios, tracking collection performance, pricing acquisition opportunities, and generating management-ready outputs.

The application combines:
- portfolio import and validation
- debtor risk scoring
- dashboard analytics
- management reporting
- acquisition valuation
- collections strategy intelligence
- role-based access control

This guide explains what each part of the application does, who should use it, and how to work with it.

## 2. Who the App Is For

The application is designed for:
- collections and portfolio operations teams
- analysts reviewing debtor quality and risk
- managers monitoring KPIs and report outputs
- acquisition teams evaluating whether a debt package is worth buying
- collections supervisors prioritizing who should be worked first and what action should happen next
- admins maintaining data, users, and internal benchmark assumptions

## 3. Main User Roles

### Visitor
Review-only demo access.

Can:
- open the dashboard
- review management report previews
- open the valuation workspace
- compare packages
- review benchmark library entries
- open the strategy workspace, collector queue, simulator, and rules library in read-only mode

Cannot:
- import data
- save valuation runs
- export reports
- edit benchmarks
- access the admin panel

### Analyst
Restricted API-oriented role.

Can:
- access selected read APIs

Cannot:
- access dashboard workflows
- access reporting and valuation workspaces
- access admin

### Manager
Operational and decision-making role.

Can:
- use dashboard and reporting
- run valuation reviews
- import valuation packages
- export valuation and management reports
- manage benchmark assumptions through the app UI
- review next-best-action recommendations
- use the collector queue and strategy simulator
- manage strategy rules through the app UI

### Admin
Full operational and administrative access.

Can:
- access everything available to Manager
- access Django admin
- manage underlying application records directly

## 4. Main Navigation

The top navigation is the fastest way to move through the product.

### Dashboard
Main operational analytics workspace.

Use it for:
- KPI monitoring
- filtering debtor populations
- viewing dynamic charts
- opening the debtor list
- moving into report workflows

### Import
Main debt portfolio import workflow.

Use it for:
- uploading structured CSV files
- validating schema and rows
- previewing data before save
- creating new operational portfolios

### Reports
Management reporting entry point.

Use it for:
- previewing executive reporting output
- exporting Excel and PDF management reports

### Valuation
Acquisition intelligence menu.

Includes:
- Workspace
- Comparison Desk
- Benchmarks
- Valuation Import (manager/admin only)

Use it for:
- reviewing package attractiveness
- pricing debt portfolio acquisitions
- comparing multiple packages
- managing benchmark assumptions

### Strategy
Collections intelligence menu.

Includes:
- Workspace
- Collector Queue
- Simulator
- Rules

Use it for:
- reviewing next-best-action recommendations for debtors
- prioritizing cases for collections teams
- comparing recovery strategies
- tuning action rules and thresholds

### Admin Panel
Visible only to admin users.

Use it for:
- user administration
- direct portfolio/debtor record management
- low-level operational maintenance

### More Actions
Secondary shortcuts for focused views and technical endpoints.

Typical items:
- High Risk Cases
- PTP Cases
- Paying Cases
- Open Cases
- API endpoints

## 5. Dashboard

URL:
`/dashboard/`

The dashboard is the central operational screen.

### What the dashboard shows

#### Filter toolbar
Filters the debtor population by:
- portfolio
- risk band
- status
- created from
- created to

Use it to narrow the analysis to a specific package or segment.

#### KPI cards
Main indicators for the filtered debtor population:
- Total Debtors
- Contact Rate
- PTP Rate
- Conversion Rate
- Recovery Rate
- Expected Collections

These cards update when filters change.

#### Portfolio Visual Analytics
Main visual analytics section.

Includes:
- Risk Band Distribution
- Status Distribution
- Outstanding Exposure by Segment

Use it to quickly understand:
- how risky the filtered population is
- what the current operating mix looks like
- where the largest exposure sits

#### Call Center Performance
Operational KPI block showing:
- Contacted Cases
- PTP Cases
- Paying Cases
- Open Cases

Use it to connect collections performance with debtor mix.

#### Priority Debtor Preview
Shortlist of high-priority records for review.

Use it to:
- spot the most urgent/high-risk debtors
- open the full debtor list when deeper review is needed

#### Risk Segment Breakdown
Aggregated table by:
- portfolio
- risk band
- status

Use it to understand where volume and exposure are concentrated.

## 6. Full Debtor List

URL:
`/dashboard/debtors/`

This is the detailed operational list view.

### What it does
- shows the full matching debtor population
- supports sorting
- supports pagination
- preserves active filters

### What you can review
- debtor name
- portfolio
- status
- days past due
- outstanding total
- risk score
- risk band

Use it when the dashboard preview is not enough and you need record-level review.

## 7. Management Reports

Preview URL:
`/reports/management/`

### What the report preview does
- summarizes KPI output in a reporting layout
- shows top risk segments
- prepares management-ready reporting output

### Exports

Available to manager/admin:
- Excel report
- PDF report

Use these outputs when you want:
- executive review
- portfolio discussion
- a clean file to send internally

Visitors can open the preview but cannot export.

## 8. Portfolio Import

URL:
`/portfolio/import/`

### Purpose
Loads structured debtor packages into the operational side of the app.

### Typical flow
1. Fill in portfolio metadata
2. Upload CSV file
3. Validate and preview
4. Confirm import

### What is validated
- required columns
- row parsing
- numeric fields
- date fields
- row-level issues

### Why this matters
The import flow prevents bad source files from being written directly into the system without review.

## 9. Valuation Workspace

URL:
`/valuation/`

This is the main acquisition intelligence screen.

### Purpose
Helps decide whether a debt package is attractive to buy.

### What it shows

#### Ranking KPI strip
Shows:
- number of portfolios ranked
- top attractiveness score
- average recovery
- average confidence score
- total face value

#### Filters and sorting
You can review the workspace by:
- signal
- recommendation
- mode
- sort order

Use this to focus on:
- strongest buy candidates
- review-only cases
- specific pricing logic modes

#### Portfolio ranking table
Ranks portfolios by:
- attractiveness
- expected recovery
- bid recommendation
- projected ROI
- confidence
- mode
- recommendation

Use it to prioritize which package deserves attention first.

#### Comparison callout
Direct shortcut to side-by-side comparison.

Use it when:
- two or three packages need direct acquisition review

## 10. Valuation Preview

Opened from the valuation workspace for a specific portfolio.

### Purpose
This is the main pricing review screen for one debt package.

### Main sections

#### Recommended Action
Top-line acquisition recommendation:
- Bid
- Hold
- Reject

This is the clearest decision layer in the valuation flow.

#### Pricing and recovery KPI cards
Includes:
- Expected Recovery
- Expected Collections
- Recommended Bid
- Max Purchase Price
- Projected ROI
- Confidence Score

Use these to understand the basic buy-side economics of the package.

#### Valuation Visual Analytics
Includes:
- Risk Mix
- Operating Signals
- Recovery vs Pricing
- Scenario ROI Ladder

Use these to understand:
- risk composition
- operational recoverability
- pricing discipline
- how aggressive bidding changes returns

#### Portfolio Signals
Shows operational mix and debtor profile metrics.

#### Key Drivers
Explains the main factors behind the recommendation.

#### Scenario Analysis
Compares multiple bid levels and shows:
- bid amount
- expected profit
- projected ROI
- break-even recovery

#### ML Baseline Forecast
Provides a first predictive layer on top of the rule-based engine.

Shows:
- model version
- predicted recovery
- predicted collections
- predicted bid
- predicted ROI
- confidence
- top predictive signals

#### ML-Ready Feature Snapshot
Shows the engineered features behind the valuation.

#### Benchmark Context
Shows whether the valuation is rule-only or benchmark-supported.

#### Saved Run Comparison
Shows previously saved valuation runs for the same package.

## 11. Valuation Comparison Desk

URL:
`/valuation/compare/`

### Purpose
Compares up to three debt packages side by side.

### What it shows
- lead vs challenger deltas
- attractiveness comparison
- expected recovery comparison
- collections comparison
- bid comparison
- ROI comparison
- recommendation comparison
- benchmark source comparison

## 12. Benchmark Library

URL:
`/valuation/benchmarks/`

### Purpose
Stores historical benchmark assumptions used by the hybrid valuation layer.

Visitors can review the benchmark library in read-only mode.
Managers and admins can manage it.

## 13. Valuation Import

URL:
`/valuation/import/`

Manager/admin only.

### Purpose
Creates a new acquisition candidate package and sends it directly into the valuation workflow.

## 14. API Layer

Key endpoints:
- `/api/portfolios/`
- `/api/debtors/`
- `/api/debtors/<id>/score/`
- `/api/kpis/overview/`
- `/api/strategy/recommendations/`
- `/api/strategy/queue/`
- `/api/strategy/simulator/`

Use the API for:
- frontend data consumption
- BI tooling
- technical review by developers
- analytics integration

## 15. Collections Strategy Workspace

URL:
`/strategy/`

### Purpose
This is the main debtor action-prioritization screen.

Use it to decide:
- which debtor should be worked first
- what the recommended next-best action is
- what channel should be used
- how much uplift the action may create

### Main sections

#### Strategy KPI cards
Shows summary metrics such as:
- debtor count
- act now cases
- average priority score
- expected uplift
- top recommended action

These cards summarize the recommended workload for the currently reviewed population.

#### Next-Best Action Ranking
Main ranked debtor table showing:
- debtor
- recommended action
- recommended channel
- priority score
- expected uplift
- reason summary

Use it to see which accounts deserve immediate attention.

#### Contact History Signals
The strategy engine also considers:
- call attempts
- last call outcome
- no-answer streak
- refusal count
- wrong-contact count
- promise-to-pay history
- note activity

This makes the recommendation more realistic than simply looking at risk score alone.

## 16. Collector Queue

URL:
`/strategy/queue/`

### Purpose
Turns ranked strategy recommendations into an operational work queue.

### What it shows
- queued cases
- act now cases
- average priority score
- expected uplift
- top action
- collector lanes
- prioritized assignment table

Use it when:
- a team lead wants to distribute work
- you want to see which cases should be worked first today

## 17. Strategy Simulator

URL:
`/strategy/simulator/`

### Purpose
Compares multiple collections strategies side by side.

### Strategies currently included
- Call-First Strategy
- Digital-First Strategy
- Settlement Strategy
- Legal Escalation Strategy
- Balanced Mixed Strategy

### What it shows
- debtor count
- expected total recovery
- expected uplift
- expected cost
- projected ROI
- best-fit segments
- winning strategy

Use it to compare operational approaches before committing the team to one playbook.

## 18. Strategy Rules

URL:
`/strategy/rules/`

### Purpose
Controls the action rules used by the strategy engine.

Visitors can review the rules in read-only mode.
Managers and admins can create or edit them.

### What the rules define
- risk band applicability
- debtor status applicability
- DPD range
- contact requirements
- recommended action
- recommended channel
- base uplift
- priority weight

Use it to tune how the collections strategy engine behaves without rewriting the whole UI.

## 19. Admin Panel

URL:
`/admin/`

Admin only.

### Purpose
Low-level maintenance and full administrative control.

## 20. Typical User Flows

### Review-only walkthrough
1. Log in as `visitor_demo`
2. Open dashboard
3. Review charts and KPI cards
4. Open report preview
5. Open valuation workspace
6. Open one portfolio valuation
7. Open comparison desk

### Operational workflow
1. Log in as manager
2. Import portfolio
3. Review dashboard
4. Open full debtor list
5. Generate reports

### Acquisition workflow
1. Log in as manager/admin
2. Open valuation import
3. Create portfolio from source package
4. Open valuation preview
5. Review recommendation, scenarios, and memo
6. Compare against other packages

### Collections strategy workflow
1. Log in as manager/admin
2. Open `Strategy -> Workspace`
3. Review next-best-action ranking and top priorities
4. Open `Collector Queue`
5. Review lane allocation and `Act Now` cases
6. Open `Simulator`
7. Compare collection strategies and review the winning option
8. Open `Rules` if a tuning change is needed

## 21. Troubleshooting

### The live demo is slow on first load
The free Render instance may be sleeping. Wait 20-30 seconds and refresh.

### A user sees a friendly access-restricted message
That is expected when the role can view but not change certain parts of the system.

### Import fails
Check:
- file size
- file format
- required columns
- numeric formatting
- UTF-8 CSV encoding

### A feature is not visible for `visitor_demo`
That may be intentional. The visitor role is designed for safe read-only review.

### A strategy recommendation looks counterintuitive
Check:
- recent call outcomes
- no-answer streak
- broken or pending promises
- whether the account is already paying or closed
- whether the rule set in `Strategy -> Rules` was changed recently

## 22. Recommended Demo Account

For public review:
- `visitor_demo / DemoPass123!`

This account is the safest way to show the app without exposing write operations or admin control.
