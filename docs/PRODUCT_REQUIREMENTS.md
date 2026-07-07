# Product Requirements

## 1. Product Goal

The Hotel Revenue Intelligence Platform provides a hotel leadership reporting layer that combines daily actuals, booking snapshots, budget targets, and last-year historicals into dashboard-ready views.

The MVP v1 goal is to give executives and operating teams a single source of truth for:

- Actual performance
- On The Books / OTB demand
- Forecasted performance
- Monthly budget targets
- Same-period last-year comparison

## 2. Target Users

| User Group | Primary Need |
|---|---|
| CEO | High-level business performance, trends, and risk visibility |
| Finance | Revenue tracking, variance analysis, and comparison against budget / last year |
| Operations | Near-term occupancy and revenue planning |
| Accounting | Source-to-output traceability and consistent month-end reporting |

## 3. Core Business Pillars

| Pillar | Meaning | Current Source |
|---|---|---|
| Actual | Completed business performance for past dates | `Daily Revenue Report` |
| OTB / On The Books | Current booking position for future stay dates | `Booking Stats Report` |
| Forecast | Projection derived from actuals plus remaining OTB | Built from `Daily Revenue Report` and `Booking Stats Report` |
| Budget | Monthly target plan | `2026 Budget PDFs` |
| Last Year | Same-period historical baseline | `2025 Monthly P&L Excel files` |

## 4. Dashboard Structure

The MVP dashboard is organized around four operational views plus an annual rollup.

| View | Purpose | Time Horizon |
|---|---|---|
| Executive Overview | Snapshot of business health across all pillars | Current + forward-looking |
| Current Month | MTD actuals versus forecast, budget, and last year | Present month |
| Next Month | Forecast / OTB planning view | Next calendar month |
| Month +2 | Early visibility for the following month | Second month ahead |
| Annual | Full-year rollup and comparison view | Full year |

## 5. Daily Performance Rules

- Past dates use `Actual`.
- Future dates use the latest available `Forecast`.
- Raw source data is never overwritten.
- Actual daily facts remain append-only in the source tab.
- Forecast snapshots remain append-only in the source tab.

## 6. Monthly Performance Rules

- Current month equals `MTD actual + remaining forecast`.
- Future months use `Forecast / OTB`.
- Comparison is only against the same month's `Budget` and the same month's `Last Year`.
- Never compare one month against another month.
- Monthly reporting must stay at hotel-month grain.

## 7. Annual Performance Rules

- The annual view is a rollup of monthly performance, not a separate raw source.
- Annual actuals should aggregate monthly actual performance.
- Annual forecast should aggregate monthly forecasted performance.
- Annual budget should aggregate monthly budget targets.
- Annual last-year should aggregate monthly historical actuals.
- Annual views should preserve hotel-level grouping and avoid cross-hotel blending.

## 8. Data Sources

| Data Source | Business Role | Current State |
|---|---|---|
| Daily Revenue Report | Daily actual performance | Current pipeline source |
| Booking Stats Report | OTB / future forecast snapshot | Current pipeline source |
| Budget PDFs | Monthly budget targets | Required for MVP v1 |
| Monthly P&L Excel files | Monthly last-year historical actuals | Required for MVP v1 |

## 9. Google Sheet Tabs Used

### 9.1 Source Tabs

| Tab | Purpose | State |
|---|---|---|
| `Daily_Hotel_Metrics` | Daily actual revenue facts | Current |
| `Booking_Forecast` | Booking snapshot facts | Current |
| `Import_Log` | Audit log of imports and validation results | Current |

### 9.2 Required Model Tabs

| Tab | Purpose | State |
|---|---|---|
| `Budget_Monthly` | Monthly budget targets | Required |
| `Historical_Monthly` | Monthly last-year historical actuals | Required |

### 9.3 Dashboard-Ready Tabs

| Tab | Purpose | State |
|---|---|---|
| `Dashboard_Daily_Performance` | Unified daily dashboard-ready table | Required |
| `Dashboard_Monthly_Performance` | Unified monthly dashboard-ready table | Required |

## 10. MVP Scope

MVP v1 includes:

- Extract daily actuals from revenue PDFs.
- Extract booking snapshots from booking stats PDFs.
- Extract monthly budget values from budget PDFs.
- Extract monthly last-year values from P&L Excel files.
- Preserve raw source rows in their source tabs.
- Prevent duplicate imports at the tab grain.
- Produce dashboard-ready monthly and daily datasets.
- Support executive, finance, operations, and accounting reporting needs.

## 11. Phase 2 Scope

Phase 2 should be treated as future work and not part of MVP v1.

| Future Item | Reason |
|---|---|
| Daily last-year comparison from daily 2025 reports | Current historical data is monthly, not daily |
| GOP, EBITDA, payroll, and net income dashboarding | Not yet supported by the current monthly model |
| Expanded scenario planning | Requires additional transformation logic |
| Automated alerting | Not part of the current pipeline architecture |
| Broader report detection beyond filename heuristics | Future robustness improvement |

## 12. Out of Scope

- Changing Google OAuth setup
- Changing OpenAI integration details
- Changing prompt schemas without coordinated extractor updates
- Overwriting raw imported data
- Guessing a hotel mapping that is not supported by `config/hotels.json`
- Replacing the current Google Sheets-based MVP datastore
- Building dashboard code inside this document stage

## 13. Important Business Rules

- Raw actuals are immutable after import.
- Raw forecast snapshots are immutable after import.
- Budget rows must stay at monthly grain.
- Historical rows must stay at monthly grain.
- Same-month comparisons only.
- No cross-month comparisons such as August versus September.
- Hotel names should be normalized to the canonical registry value before downstream grouping.
- Unknown hotel names should be preserved as raw source values until the registry is updated.
- Duplicate prevention must remain based on the configured grain for each tab.

## 14. Implementation Roadmap

1. Ingest daily revenue reports into `Daily_Hotel_Metrics`.
2. Ingest booking stats reports into `Booking_Forecast`.
3. Ingest budget PDFs into `Budget_Monthly`.
4. Ingest monthly P&L Excel files into `Historical_Monthly`.
5. Build `Dashboard_Daily_Performance` from actual and forecast source tabs.
6. Build `Dashboard_Monthly_Performance` from actual, forecast, budget, and historical tabs.
7. Rebuild the dashboard views on top of the dashboard-ready tabs.

## 15. Requirement Traceability

This document is aligned with:

- `docs/DATA_MODEL.md`
- `docs/DASHBOARD_SPEC.md`
- `docs/PROJECT_RECAP.md`
- `AGENTS.md`
