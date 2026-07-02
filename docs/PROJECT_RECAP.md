# Project Recap

## Project Purpose

The repository automates hotel report ingestion. It reads PDF reports, extracts structured data with OpenAI Vision, validates the extracted results, and writes approved rows into Google Sheets.

The current scope is:

- Revenue Report ingestion
- Booking Stats Report ingestion
- Import logging for both flows
- Local JSON output for debugging and traceability

## Current Architecture

The repository uses a simple layered pipeline:

| Layer | Responsibility |
|---|---|
| `services/` | PDF rendering, OpenAI Vision, and report type detection |
| `extractors/` | Report-specific extraction entry points |
| `models/` | Row mapping and shared status constants |
| `validators/` | Data quality rules |
| `writers/` | Google Sheets auth and append helpers |
| `main.py` | Orchestrates the flow end to end |

## Completed Features

- Revenue Report extraction from a PDF page image.
- Revenue validation before append.
- Booking Stats raw extraction from the first 3 pages.
- Booking row mapping into the `Booking_Forecast` schema.
- Booking validation after mapping.
- Google Sheets appends for `Daily_Hotel_Metrics`, `Booking_Forecast`, and `Import_Log`.
- Duplicate prevention for revenue and booking sheet writes.
- Centralized import status strings in `models/status.py`.
- Local JSON output for extractor debugging.

## Revenue Report Pipeline

```text
sample PDF
  -> pdf_page_to_png(page 1)
  -> OpenAI Vision extraction
  -> revenue_validator
  -> Daily_Hotel_Metrics append or duplicate skip
  -> Import_Log append
  -> output/revenue_report_extracted.json
```

### Current behavior

- The first page is the only page processed.
- `extractors/revenue_report.py` adds source metadata and validation status.
- `main.py` prints the resulting JSON and then writes to Google Sheets when validation passes.
- Duplicate detection happens in `writers/google_sheets.py` before append.

## Booking Stats Pipeline

```text
sample PDF
  -> pdf_page_to_png(page 1..3)
  -> OpenAI Vision extraction
  -> raw_rows
  -> booking_mapping
  -> booking_validator
  -> Booking_Forecast batch append
  -> Import_Log append
  -> output/booking_stats_extracted.json (via extractor __main__ only)
```

### Current behavior

- `extractors/booking_stats.py` returns raw extracted data only.
- `main.py` performs mapping and validation.
- `writers/google_sheets.py` batch appends booking rows using `append_rows`.
- Booking success prints appended/skipped counts.
- Booking success also prints a validated JSON payload in the console path.

## Validation Flow

### Revenue

- Validates required fields.
- Validates occupancy, ADR, and RevPAR relationships.
- Marks the payload `VALIDATED` or `VALIDATION_FAILED`.

### Booking

- Validates that mapped rows exist.
- Checks duplicate rows within the mapped set.
- Checks required mapped fields and simple numeric ranges.
- Does not currently enforce a `room_revenue = sold * avg_room_revenue` business formula.

## Google Sheets Flow

`writers/google_sheets.py` is the only module that writes to Sheets.

| Function | Target Tab | Current Behavior |
|---|---|---|
| `append_daily_hotel_metrics()` | `Daily_Hotel_Metrics` | Appends one row unless an existing record matches the duplicate key. |
| `append_booking_forecast_rows()` | `Booking_Forecast` | Batch appends non-duplicate rows. |
| `append_import_log()` | `Import_Log` | Always appends a new log row. |

## Import_Log Flow

Every import attempt ends with an `Import_Log` row when the code reaches the logging step.

Typical log data includes:

- `import_time`
- `hotel_name`
- `report_type`
- `business_date`
- `source_file_name`
- `status`
- `action`
- `notes`

## Duplicate Prevention

| Target | Duplicate Key | Notes |
|---|---|---|
| `Daily_Hotel_Metrics` | `business_date + hotel_name + report_type` | Checked against existing sheet records before append. |
| `Booking_Forecast` | `hotel_name + stay_date + source_file_name` | Checked against existing records and rows queued in the same batch. |

## Known Limitations

| Limitation | Current State |
|---|---|
| Automated tests | No test suite is currently defined. |
| Booking page coverage | Only the first 3 pages are processed. |
| Booking header helper | `booking_header_analyzer.py` is standalone and not orchestrated. |
| Report detection | Uses file-name heuristics only. |
| Config management | `config/settings.py` is empty. |
| Shared metrics model | `models/hotel_metrics.py` is empty. |
| Dependency manifest | `requirements.txt` is empty. |

## Current Technical Debt

- The repository relies on manual local execution for verification.
- `main.py` contains sample input paths, so the default run is tied to the current sample files.
- The booking pipeline duplicates some import-log payload construction in `main.py`.
- Several placeholder files exist but do not yet carry implementation:
  - `config/settings.py`
  - `models/hotel_metrics.py`

## Next Roadmap

The following items are natural next steps based on the current codebase:

- Add an automated test suite.
- Populate or remove placeholder modules.
- Decide whether `booking_header_analyzer.py` should be part of the supported runtime path.
- Expand report detection if additional report names or sources are introduced.
- Review whether booking page coverage should remain fixed at 3 pages.
- Add more robust error reporting around external OpenAI and Google Sheets failures.
