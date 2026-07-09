# Looker Studio Setup

## Purpose

This document defines the MVP Looker Studio dashboard setup for the Hotel Revenue Intelligence Platform.

The dashboard must use only dashboard-ready semantic-layer tabs:

- `Dashboard_Daily_Performance`
- `Dashboard_Monthly_Performance`

Do not connect charts to raw ETL tabs.

## Current Dashboard-Ready Tab Headers

### `Dashboard_Daily_Performance`

| Field |
|---|
| `hotel_name` |
| `date` |
| `month_number` |
| `month_name` |
| `data_type` |
| `rooms_sold` |
| `occupancy_pct` |
| `adr` |
| `revpar` |
| `room_revenue` |
| `total_revenue` |
| `source_file_name` |
| `forecast_snapshot_date` |
| `date_status` |
| `display_data_type` |
| `import_time` |

### `Dashboard_Monthly_Performance`

| Field |
|---|
| `hotel_name` |
| `year` |
| `month_number` |
| `month_name` |
| `actual_room_revenue` |
| `forecast_remaining_room_revenue` |
| `projected_room_revenue` |
| `budget_room_revenue` |
| `last_year_room_revenue` |
| `actual_total_revenue` |
| `budget_total_revenue` |
| `last_year_total_revenue` |
| `actual_occupancy` |
| `budget_occupancy` |
| `last_year_occupancy` |
| `actual_adr` |
| `budget_adr` |
| `last_year_adr` |
| `actual_revpar` |
| `budget_revpar` |
| `last_year_revpar` |
| `budget_variance` |
| `yoy_variance` |
| `budget_variance_amount` |
| `budget_variance_pct` |
| `yoy_variance_amount` |
| `yoy_variance_pct` |
| `forecast_completion_pct` |
| `month_status` |
| `import_time` |
| `status` |
| `notes` |

## Data Source Setup

1. Open Looker Studio and create a new report.
2. Add a Google Sheets connector.
3. Connect the Google Sheet that contains this project’s dashboard tabs.
4. Create two data sources:
   - `Dashboard_Daily_Performance`
   - `Dashboard_Monthly_Performance`
5. Confirm that date fields are typed as dates, numeric fields are typed as numbers, and percentage/currency metrics are recognized correctly.
6. Use the two dashboard-ready tabs directly. Do not connect raw tabs.

## Field Mapping

### `Dashboard_Daily_Performance`

| Field | Looker Type | Aggregation | Usage Notes |
|---|---|---:|---|
| `hotel_name` | Text | None | Primary hotel filter and grouping key. |
| `date` | Date | None | Daily grain key. |
| `month_number` | Number | None | Supports month filtering and sorting. |
| `month_name` | Text | None | Display label only. |
| `data_type` | Text | None | Core semantic type: `Actual` or `Forecast`. |
| `rooms_sold` | Number | Sum | Daily volume metric. |
| `occupancy_pct` | Percent | Average | Daily occupancy metric. |
| `adr` | Currency | Average | Daily ADR metric. |
| `revpar` | Currency | Average | Daily RevPAR metric. |
| `room_revenue` | Currency | Sum | Daily room revenue. |
| `total_revenue` | Currency | Sum | Actual total revenue only; forecast rows may be blank. |
| `source_file_name` | Text | None | Traceability field. |
| `forecast_snapshot_date` | Date | None | Latest forecast snapshot date used for the row. |
| `date_status` | Text | None | `Past`, `Today`, or `Future`. |
| `display_data_type` | Text | None | Dashboard-friendly label such as `Actual`, `Current OTB`, or `Forecast`. |
| `import_time` | Text | None | Audit field only. |

### `Dashboard_Monthly_Performance`

| Field | Looker Type | Aggregation | Usage Notes |
|---|---|---:|---|
| `hotel_name` | Text | None | Primary hotel filter and grouping key. |
| `year` | Number | None | Monthly rollup year. |
| `month_number` | Number | None | Monthly rollup month index. |
| `month_name` | Text | None | Display label only. |
| `actual_room_revenue` | Currency | Sum | Month-to-date actual room revenue. |
| `forecast_remaining_room_revenue` | Currency | Sum | Remaining forecast room revenue for the month. |
| `projected_room_revenue` | Currency | Sum | `actual_room_revenue + forecast_remaining_room_revenue`. |
| `budget_room_revenue` | Currency | Sum | Budget comparison field. |
| `last_year_room_revenue` | Currency | Sum | Prior-year comparison field. |
| `actual_total_revenue` | Currency | Sum | Month-to-date actual total revenue. |
| `budget_total_revenue` | Currency | Sum | Budget total revenue. |
| `last_year_total_revenue` | Currency | Sum | Prior-year total revenue. |
| `actual_occupancy` | Percent | Average | Actual occupancy. |
| `budget_occupancy` | Percent | Average | Budget occupancy. |
| `last_year_occupancy` | Percent | Average | Prior-year occupancy. |
| `actual_adr` | Currency | Average | Actual ADR. |
| `budget_adr` | Currency | Average | Budget ADR. |
| `last_year_adr` | Currency | Average | Prior-year ADR. |
| `actual_revpar` | Currency | Average | Actual RevPAR. |
| `budget_revpar` | Currency | Average | Budget RevPAR. |
| `last_year_revpar` | Currency | Average | Prior-year RevPAR. |
| `budget_variance` | Currency | Sum | Backward-compatible variance field. |
| `yoy_variance` | Currency | Sum | Backward-compatible year-over-year variance field. |
| `budget_variance_amount` | Currency | Sum | Primary budget variance amount. |
| `budget_variance_pct` | Percent | Average | Percent variance vs budget. |
| `yoy_variance_amount` | Currency | Sum | Primary YoY variance amount. |
| `yoy_variance_pct` | Percent | Average | Percent variance vs last year. |
| `forecast_completion_pct` | Percent | Average | Completion ratio for the month. |
| `month_status` | Text | None | `Past`, `Current`, or `Future`. |
| `import_time` | Text | None | Audit field only. |
| `status` | Text | None | Import/transform status. |
| `notes` | Text | None | Import/transform notes. |

## Recommended Page Layout

### 1. Executive Overview

Recommended components:

- Hotel filter
- Month filter
- Projected Room Revenue scorecard
- Budget Room Revenue scorecard
- Budget Variance scorecard
- YoY Variance scorecard
- Forecast Completion % scorecard
- Month Status scorecard or text box
- Monthly comparison table from `Dashboard_Monthly_Performance`
- Daily performance table or chart from `Dashboard_Daily_Performance`

Recommended use:

- Primary landing page for executives.
- Show the latest business month and top-line progress.

### 2. Current Month

Recommended components:

- Daily actual/forecast trend chart
- Rooms sold time series
- Occupancy time series
- ADR time series
- RevPAR time series
- Room revenue time series
- `data_type` / `display_data_type` breakdown table or stacked chart

Recommended use:

- Monitor the current month at daily grain.
- Show `Actual` vs `Current OTB` without rebuilding logic in Looker.

### 3. Next Month

Recommended components:

- Monthly summary cards
- Monthly comparison table filtered to the next month
- Forecast completion or projected revenue chart

### 4. Month +2

Recommended components:

- Same layout as Next Month
- Month-specific filter preset to the second future month

### 5. Annual / YTD

Recommended components:

- Annual summary cards
- Year filter
- Monthly revenue trend
- Budget vs projected vs last year comparison table

## Filters

Use these filters consistently across pages:

- `hotel_name`
- `year`
- `month_name`
- `data_type`
- `date_status`

Recommended behavior:

- `hotel_name` should be a global report filter.
- `year` and `month_name` should drive the monthly pages.
- `data_type` and `date_status` should drive the daily pages.

## Currency Fields

Format these fields as currency:

- `room_revenue`
- `total_revenue`
- `actual_room_revenue`
- `forecast_remaining_room_revenue`
- `projected_room_revenue`
- `budget_room_revenue`
- `last_year_room_revenue`
- `actual_total_revenue`
- `budget_total_revenue`
- `last_year_total_revenue`
- `actual_adr`
- `budget_adr`
- `last_year_adr`
- `actual_revpar`
- `budget_revpar`
- `last_year_revpar`
- `budget_variance`
- `yoy_variance`
- `budget_variance_amount`
- `yoy_variance_amount`

## Percent Fields

Format these fields as percent:

- `occupancy_pct`
- `actual_occupancy`
- `budget_occupancy`
- `last_year_occupancy`
- `budget_variance_pct`
- `yoy_variance_pct`
- `forecast_completion_pct`

## Do Not Build In Looker

Do not implement these in Looker Studio:

- actual/forecast merging logic
- latest snapshot selection logic
- budget matching logic
- last-year matching logic
- month comparison logic

These responsibilities already live in the Python transformers.

## Validation Checklist

Before publishing the dashboard, confirm:

- July 5, July 6, and July 7 show as `Actual`
- July 8 shows as `Forecast` and `Current OTB`
- July, August, and September monthly rows appear
- budget and last-year values are present in the monthly table
- no raw tabs are used in charts

## Exact Manual Steps

1. Open Looker Studio.
2. Create a new report.
3. Connect the Google Sheet.
4. Add `Dashboard_Daily_Performance` as the first data source.
5. Add `Dashboard_Monthly_Performance` as the second data source.
6. Verify field types:
   - dates as Date
   - counts and revenue fields as Number or Currency
   - occupancy and completion fields as Percent
7. Build the Executive Overview page first.
8. Add the Current Month page next.
9. Add Next Month, Month +2, and Annual / YTD pages.
10. Run the validation checklist against the final report.

