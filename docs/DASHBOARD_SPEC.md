# Dashboard Spec

## 1. Dashboard Goal

Build an MVP executive dashboard on top of the current Google Sheet tabs so leadership can review revenue, booking pace, and import health without waiting for a separate warehouse.

The dashboard should answer:

- How is the hotel performing today and over the selected period?
- How are revenue and booking trends changing by hotel and date?
- Is the data feed current and trustworthy?

## 2. Target Users

| User | Primary Need |
|---|---|
| CEO | Fast executive summary of hotel performance, trends, and exceptions |
| Finance | Revenue visibility, consistency checks, and period comparisons |
| Operations | Booking pace, occupancy trend, and upcoming demand signal |
| Accounting | Import audit trail, data freshness, and exception review |

## 3. Pages

### 3.1 Executive Overview

Purpose: One-screen summary across revenue, booking, and data freshness.

#### KPIs

- Latest revenue
- Latest occupancy
- Latest ADR
- Latest RevPAR
- Latest booking sold
- Latest import status

#### Charts

- Revenue trend over time
- Occupancy trend over time
- Booking sold trend over time
- Import volume/status summary

### 3.2 Revenue Dashboard

Purpose: Analyze revenue performance from `Daily_Hotel_Metrics`.

#### KPIs

- Room revenue
- Gross revenue
- F&B revenue
- Beverage revenue
- Other income
- Rooms sold
- Rooms available
- Occupancy %
- ADR
- RevPAR
- Total guests

#### Charts

- Revenue trend by date
- Revenue component breakdown
- Occupancy vs ADR trend
- Rooms sold vs rooms available

### 3.3 Booking Forecast

Purpose: Review booking pace and forecast information from `Booking_Forecast`.

#### KPIs

- Sold
- Occupancy %
- Room revenue
- Average room revenue
- Group rooms not sold
- Groups total
- Groups available
- Groups occupancy %

#### Charts

- Booking sold trend by stay date
- Occupancy trend by stay date
- Room revenue trend by stay date
- Group availability trend

### 3.4 Import Monitor

Purpose: Monitor pipeline freshness and exceptions from `Import_Log`.

#### KPIs

- Total imports
- Successful imports
- Validation failures
- Extraction failures
- Duplicate skips
- Latest import time

#### Charts

- Import status over time
- Imports by report type
- Failures by day
- Duplicate skips by day

## 4. Filters

| Filter | Status | Notes |
|---|---|---|
| Hotel | Available | Use the `hotel_name` column present in all three tabs |
| Date range | Available | Use `business_date`, `stay_date`, or `import_time` depending on page |
| Report type | Available | Use `report_type` in `Daily_Hotel_Metrics` and `Import_Log`; Booking forecast is implicitly booking-only |

## 5. Data Source Mapping

### 5.1 `Daily_Hotel_Metrics`

Current source fields available from the revenue pipeline:

| Sheet Column | Dashboard Use | Availability |
|---|---|---|
| `business_date` | Date filter, trends | Available |
| `hotel_name` | Hotel filter | Available |
| `report_type` | Report filter | Available |
| `room_revenue` | Revenue KPI, trend | Available |
| `gross_revenue` | Revenue KPI, trend | Available |
| `fb_revenue` | Revenue KPI, trend | Available |
| `beverage_revenue` | Revenue KPI, trend | Available |
| `other_income` | Revenue KPI, trend | Available |
| `rooms_sold` | Volume KPI, trend | Available |
| `rooms_occupied` | Volume KPI, trend | Available |
| `rooms_available` | Capacity KPI, trend | Available |
| `rooms_vacant` | Capacity KPI, trend | Available |
| `occupancy_pct` | KPI, trend | Available |
| `adr` | KPI, trend | Available |
| `revpar` | KPI, trend | Available |
| `total_guests` | KPI, trend | Available |
| `cancelled_reservations` | Exception KPI | Available |
| `no_shows` | Exception KPI | Available |
| `walk_ins` | Exception KPI | Available |
| `ptd_room_revenue` | Future KPI | Partial in source output, not currently reliable for dashboard use |
| `ytd_room_revenue` | Future KPI | Partial in source output, not currently reliable for dashboard use |
| `source_file_name` | Audit trail | Available |
| `source_email_subject` | Future metadata | Not currently populated |
| `source_email_sender` | Future metadata | Not currently populated |
| `import_time` | Freshness / audit | Available |
| `status` | Import monitor | Available |
| `notes` | Import monitor | Available |

### 5.2 `Booking_Forecast`

Current source fields available from the booking pipeline:

| Sheet Column | Dashboard Use | Availability |
|---|---|---|
| `report_date` | Page context, trend grouping | Available, but can be null in current extracts |
| `hotel_name` | Hotel filter | Available |
| `stay_date` | Date filter, booking trend axis | Available |
| `source_file_name` | Audit trail | Available |
| `import_time` | Freshness / audit | Available |
| `status` | Import monitor | Available |
| `notes` | Import monitor | Available |
| `gtd` | Booking KPI | Available |
| `non` | Booking KPI | Available |
| `total` | Booking KPI | Available |
| `overs` | Booking KPI | Available |
| `deps` | Booking KPI | Available |
| `guests` | Booking KPI | Available |
| `sold` | Booking KPI, trend | Available |
| `occupancy_pct` | KPI, trend | Available |
| `room_revenue` | KPI, trend | Available |
| `avg_room_revenue` | KPI, trend | Available |
| `group_rooms_not_sold` | KPI | Available |
| `groups_total` | KPI | Available |
| `groups_available` | KPI | Available |
| `groups_occupancy_pct` | KPI | Available |

### 5.3 `Import_Log`

Current source fields available for monitoring:

| Sheet Column | Dashboard Use | Availability |
|---|---|---|
| `import_time` | Freshness / timeline | Available |
| `hotel_name` | Filter / grouping | Available |
| `report_type` | Filter / grouping | Available |
| `business_date` | Date grouping | Available |
| `source_file_name` | Audit trail | Available |
| `status` | Status KPI | Available |
| `action` | Status KPI | Available |
| `notes` | Exception details | Available |

## 6. Refresh Behavior

### MVP

- Dashboard reads directly from the three Google Sheet tabs.
- Refresh is manual or on page reload, depending on the visualization tool.
- Freshness should be displayed using `import_time` from `Import_Log` and the data tabs.

### Future

- Scheduled refresh.
- Cache layer or warehouse sync.
- Incremental refresh by new import time.

## 7. MVP Scope

The MVP dashboard should include:

- The four pages listed above.
- Metrics only from columns that already exist in the current tabs.
- Filters for hotel, date range, and report type.
- Simple line, bar, and summary charts.
- Import freshness and failure visibility.

The MVP should not require:

- New extractors
- New Google Sheet tabs
- New prompts
- New data enrichment jobs
- New write logic

## 8. Future Enhancements

- Forecast variance vs actuals.
- Multi-hotel comparison views.
- Weekly and monthly rollups.
- Drill-down into source rows from a chart click.
- Alerting for failed imports or stale data.
- Email subject/sender metadata once it is populated in the pipeline.
- PTD/YTD analytics if those fields become reliable enough for reporting.
- Role-based views for executive vs operational users.

## 9. Open Questions

1. Which dashboarding tool will host the MVP?
2. Should `report_type` be shown to end users on every page, or only in filters and metadata?
3. Should `Booking_Forecast` use `stay_date` only, or also surface `report_date` when present?
4. Should null `report_date` values in `Booking_Forecast` block dashboard ingestion or be tolerated?
5. Should import errors from `Import_Log` be exposed to all users or only operations/accounting?
6. Do we need a hotel comparison view now, or should MVP stay single-hotel focused?

Recommended MVP dashboard tool: Looker Studio connected directly to Google Sheets.
Next.js dashboard should be considered Phase 2 after KPI layout and stakeholder feedback are confirmed.