# Data Model

## 1. Business Goal

The Hotel Revenue Intelligence Platform must support five business views:

| View | Meaning | Status |
|---|---|---|
| Actual | Completed business-day performance | Current |
| OTB / On The Books | Current booking position for future stay dates | Current |
| Forecast | Projection built from actuals plus remaining OTB | Future/partial |
| Budget | Monthly target plan | Future |
| Last Year | Monthly historical comparison baseline | Future |

### Model Intent

The data model should allow leadership to compare:

- Actual performance against budget
- Actual performance against last year
- Forecast versus budget for future months
- OTB position for short-term operational planning

## 2. Source Reports

| Source Report | Business Meaning | Current State |
|---|---|---|
| Daily Revenue Report | Actual completed business day | Implemented in current pipeline |
| Booking Stats Report | OTB / forecast snapshot for future stay dates | Implemented in current pipeline |
| 2026 Budget PDFs | Monthly budget targets | Future |
| 2025 P&L Excel files | Monthly last-year historical actuals | Future |

### Source-to-Model Interpretation

```text
Daily Revenue Report   -> actual daily facts
Booking Stats Report   -> snapshot-based future stay facts
2026 Budget PDFs       -> monthly budget fact table
2025 P&L Excel files   -> monthly historical fact table
```

## 3. Existing Tabs

These tabs already exist in the current implementation:

| Tab | Purpose | Status |
|---|---|---|
| `Daily_Hotel_Metrics` | Daily actual revenue facts | Current |
| `Booking_Forecast` | Booking / OTB snapshot rows | Current |
| `Import_Log` | Pipeline audit log | Current |

## 4. New Required Tabs

These tabs are required by the finalized dashboard model:

| Tab | Purpose | Status |
|---|---|---|
| `Budget_Monthly` | Monthly budget targets | Future/required |
| `Historical_Monthly` | Monthly last-year actuals | Future/required |
| `Dashboard_Daily_Performance` | Unified daily dashboard-ready facts | Future/required |
| `Dashboard_Monthly_Performance` | Unified monthly dashboard-ready facts | Future/required |

## 5. Primary Keys

| Tab | Primary Key | Notes |
|---|---|---|
| `Daily_Hotel_Metrics` | `hotel_name + business_date + report_type` | Current implementation key |
| `Booking_Forecast` | `hotel_name + stay_date + snapshot_date + source_file_name` | Finalized model requires `snapshot_date`; current implementation does not store it yet |
| `Budget_Monthly` | `hotel_name + year + month_number` | Required for monthly budget grain |
| `Historical_Monthly` | `hotel_name + year + month_number` | Required for monthly historical grain |
| `Dashboard_Daily_Performance` | `hotel_name + date` | Dashboard-ready daily grain |
| `Dashboard_Monthly_Performance` | `hotel_name + year + month_number` | Dashboard-ready monthly grain |

## 6. Table Schemas

### 6.1 `Budget_Monthly`

Monthly budget fact table.

| Column | Type / Meaning | Status |
|---|---|---|
| `hotel_name` | Hotel identifier | Required |
| `year` | Budget year | Required |
| `month_number` | Month number 1-12 | Required |
| `month_name` | Month label | Required |
| `available_rooms` | Budgeted available rooms | Required |
| `rooms_sold` | Budgeted rooms sold | Required |
| `occupancy_pct` | Budget occupancy percentage | Required |
| `adr` | Budget ADR | Required |
| `revpar` | Budget RevPAR | Required |
| `room_revenue` | Budget room revenue | Required |
| `fb_revenue` | Budget F&B revenue | Required |
| `misc_revenue` | Budget miscellaneous revenue | Required |
| `total_revenue` | Budget total revenue | Required |
| `source_file_name` | Source budget file | Required |
| `import_time` | Ingestion timestamp | Required |
| `status` | Load status | Required |
| `notes` | Load notes | Required |

### 6.2 `Historical_Monthly`

Monthly last-year actuals fact table.

| Column | Type / Meaning | Status |
|---|---|---|
| `hotel_name` | Hotel identifier | Required |
| `year` | Historical year | Required |
| `month_number` | Month number 1-12 | Required |
| `month_name` | Month label | Required |
| `rooms_sold` | Monthly rooms sold | Required |
| `occupancy_pct` | Monthly occupancy percentage | Required |
| `adr` | Monthly ADR | Required |
| `revpar` | Monthly RevPAR | Required |
| `room_revenue` | Monthly room revenue | Required |
| `total_revenue` | Monthly total revenue | Required |
| `source_file_name` | Source P&L file | Required |
| `import_time` | Ingestion timestamp | Required |
| `status` | Load status | Required |
| `notes` | Load notes | Required |

### 6.3 `Dashboard_Daily_Performance`

Dashboard-ready daily grain. This is the unified daily view that should choose actuals when available and otherwise use the latest forecast snapshot.

| Column | Type / Meaning | Status |
|---|---|---|
| `hotel_name` | Hotel identifier | Required |
| `date` | Daily grain date | Required |
| `month_number` | Month number 1-12 | Required |
| `month_name` | Month label | Required |
| `data_type` | `Actual` or `Forecast` | Required |
| `rooms_sold` | Daily rooms sold | Required |
| `occupancy_pct` | Daily occupancy percentage | Required |
| `adr` | Daily ADR | Required |
| `revpar` | Daily RevPAR | Required |
| `room_revenue` | Daily room revenue | Required |
| `total_revenue` | Daily total revenue | Required for Actual rows; nullable for Forecast rows |
| `source_file_name` | Source file used | Required |
| `forecast_snapshot_date` | Forecast snapshot date when `data_type = Forecast` | Required for forecast rows |
| `import_time` | Transformation timestamp | Required |

### 6.4 `Dashboard_Monthly_Performance`

Dashboard-ready monthly grain for comparing actual, forecast, budget, and last year.

| Column | Type / Meaning | Status |
|---|---|---|
| `hotel_name` | Hotel identifier | Required |
| `year` | Reporting year | Required |
| `month_number` | Month number 1-12 | Required |
| `month_name` | Month label | Required |
| `actual_room_revenue` | MTD or final actual room revenue | Required |
| `forecast_remaining_room_revenue` | Remaining forecast room revenue | Required |
| `projected_room_revenue` | `MTD actual room revenue + remaining forecast room revenue` | Required |
| `budget_room_revenue` | Monthly budget room revenue | Required |
| `last_year_room_revenue` | Same month last-year room revenue | Required |
| `actual_total_revenue` | Monthly actual total revenue | Required |
| `budget_total_revenue` | Monthly budget total revenue | Required |
| `last_year_total_revenue` | Same month last-year total revenue | Required |
| `actual_occupancy` | Monthly actual occupancy | Required |
| `budget_occupancy` | Monthly budget occupancy | Required |
| `last_year_occupancy` | Same month last-year occupancy | Required |
| `actual_adr` | Monthly actual ADR | Required |
| `budget_adr` | Monthly budget ADR | Required |
| `last_year_adr` | Same month last-year ADR | Required |
| `actual_revpar` | Monthly actual RevPAR | Required |
| `budget_revpar` | Monthly budget RevPAR | Required |
| `last_year_revpar` | Same month last-year RevPAR | Required |
| `budget_variance` | Comparison metric versus budget | Required |
| `yoy_variance` | Comparison metric versus last year | Required |
| `import_time` | Transformation timestamp | Required |
| `status` | Transformation status | Required |
| `notes` | Transformation notes | Required |

## 7. Business Rules

### 7.1 Raw Data Protection

- Never overwrite raw actuals.
- Never overwrite raw forecast snapshots.
- Keep source tabs append-only.

### 7.2 Daily Dashboard Rule

- Use `Actual` when available.
- Otherwise use the latest forecast snapshot.

### 7.3 Monthly Projection Rule

`projected_room_revenue = MTD actual room revenue + remaining forecast room revenue`

### 7.4 Comparison Rules

- Compare July, August, and September only with their own budget and same-month last year.
- Never compare August against September.
- For future months, compare OTB / forecast room revenue against budget room revenue.
- Last-year data is currently July through December only.

## 8. Dashboard Page Mapping

| Dashboard Page | Data Model Focus | Notes |
|---|---|---|
| July page | July monthly performance | Compare July actual/forecast against July budget and July last year |
| August page | August monthly performance | Compare August actual/forecast against August budget and August last year |
| September page | September monthly performance | Compare September actual/forecast against September budget and September last year |
| Annual page | All months / year rollup | Aggregate monthly performance across the year |

## 9. Implementation Sequence

1. Create new Google Sheet tabs.
2. Add `snapshot_date` to `Booking_Forecast`.
3. Build `Budget_Monthly` importer.
4. Build `Historical_Monthly` importer.
5. Build dashboard transformation script.
6. Rebuild Looker Studio using dashboard-ready tabs.

## 10. Current Implementation vs Finalized Model

| Area | Current State | Finalized Target |
|---|---|---|
| Actuals | Implemented in `Daily_Hotel_Metrics` | Continue as source of truth for actual daily facts |
| OTB / Forecast | Implemented in `Booking_Forecast` without `snapshot_date` | Add `snapshot_date` and preserve snapshots |
| Budget | Not implemented | Add `Budget_Monthly` |
| Last Year | Not implemented | Add `Historical_Monthly` |
| Dashboard-ready tables | Not implemented | Add `Dashboard_Daily_Performance` and `Dashboard_Monthly_Performance` |

## 11. Open Questions / Future

- Daily last-year comparison requires daily 2025 reports, not only monthly P&L.
- GOP, EBITDA, payroll, and net income should be Phase 2 after monthly 2026 P&Ls arrive.
- The exact transformation owner for dashboard-ready tables is still unspecified.
- The dashboard should confirm whether forecast snapshots are daily, weekly, or ad hoc once `snapshot_date` is added.

## 12. Hotel Normalization Registry

The repository now includes `config/hotels.json` as the canonical hotel registry.

### 12.1 Purpose

`config/hotels.json` stores the standardized hotel name as the top-level key and keeps the property metadata alongside it.

Example shape:

```json
{
  "Residence Inn Laval": {
    "hotel_id": 1,
    "brand": "Marriott",
    "city": "Laval",
    "province": "QC",
    "rooms": 111
  }
}
```

### 12.2 Current Consumers

| Module | Uses `config/hotels.json`? | Notes |
|---|---|---|
| `extractors/booking_stats.py` | No | Booking extraction currently returns the hotel name from the source report. |
| `extractors/budget_report.py` | Yes | Budget extraction normalizes the source hotel name to the canonical registry key. |
| `validators/` | No | Validators check structure and ranges only. |
| `writers/` | No | Writers append rows and perform duplicate detection on existing sheet keys. |
| `main.py` | No | `main.py` orchestrates routing but does not normalize hotel names yet. |

### 12.3 Standardization Rule

- Canonical hotel names are the exact JSON keys in `config/hotels.json`.
- Any alias, abbreviation, or source-specific variation should be normalized to the canonical key before a row is treated as final.
- Downstream grouping, dashboarding, and duplicate logic should use the canonical name, not a guessed variation.

### 12.4 Add a New Hotel

1. Add a new top-level key to `config/hotels.json`.
2. Use the exact canonical display name as the key.
3. Add the property metadata fields needed by the platform.
4. Update any documentation, mappings, or tests that depend on the hotel registry.

### 12.5 Unknown Hotel Behavior

- If a source hotel name is not present in the registry, keep the raw source value rather than inventing a match.
- Mark the record as needing review if normalization is implemented in a future runtime path.
- Do not merge an unknown hotel into an existing property just to force a match.

### 12.6 Risk If Missing

- Missing registry coverage can split one property across multiple names.
- That fragmentation can break duplicate detection, dashboard grouping, and month-over-month comparisons.
- The safest fallback is to preserve the raw name and surface the mismatch for manual follow-up.
