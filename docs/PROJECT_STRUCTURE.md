# Project Structure

## Current Folder Tree

```text
hotel-data-platform/
|-- AGENTS.md
|-- config/
|   `-- settings.py
|-- credentials/
|   |-- credentials.json
|   `-- token.json
|-- docs/
|   |-- ARCHITECTURE_DECISIONS.md
|   |-- PROJECT_RECAP.md
|   `-- PROJECT_STRUCTURE.md
|-- extractors/
|   |-- __init__.py
|   |-- booking_header_analyzer.py
|   |-- booking_stats.py
|   `-- revenue_report.py
|-- main.py
|-- models/
|   |-- booking_mapping.py
|   |-- hotel_metrics.py
|   `-- status.py
|-- output/
|   |-- booking_header_analysis.json
|   |-- booking_stats_extracted.json
|   |-- pages/
|   |   |-- BOOKING STATS REPORT - JUNE 29 2026_page_1.png
|   |   |-- BOOKING STATS REPORT - JUNE 29 2026_page_2.png
|   |   |-- BOOKING STATS REPORT - JUNE 29 2026_page_3.png
|   |   `-- REVENUE REPORT - JUNE 29 2026_page_1.png
|   `-- revenue_report_extracted.json
|-- prompts/
|   |-- booking_header_prompt.txt
|   |-- booking_stats_prompt.txt
|   `-- revenue_report_prompt.txt
|-- samples/
|   |-- BOOKING STATS REPORT - JUNE 29 2026.pdf
|   |-- REVENUE REPORT - JUNE 29 2026.pdf
|   `-- email.txt
|-- services/
|   |-- __init__.py
|   |-- pdf_service.py
|   |-- report_detector.py
|   `-- vision_service.py
|-- validators/
|   |-- __init__.py
|   |-- booking_validator.py
|   `-- revenue_validator.py
|-- venv/
`-- writers/
    |-- __init__.py
    `-- google_sheets.py
```

## Top-Level Files

| File | Responsibility | Status |
|---|---|---|
| `main.py` | Runtime orchestrator and entry point | Active |
| `README.md` | Repository readme | Empty |
| `requirements.txt` | Dependency manifest | Empty |
| `.gitignore` | Ignored/generated file rules | Active |
| `.env` | Local environment variables | Present locally, not for version control |

## Folder Explanations

### `config/`

Configuration placeholders. `settings.py` currently exists but is empty.

### `credentials/`

Local Google OAuth material used by the Sheets writer. The repository ignores this folder in Git.

### `docs/`

Project documentation for both humans and AI agents.

### `extractors/`

Report-specific extraction entry points.

| Module | Responsibility | Status |
|---|---|---|
| `revenue_report.py` | Extract and validate the revenue report | Active |
| `booking_stats.py` | Extract raw booking rows and report metadata | Active |
| `booking_header_analyzer.py` | Standalone booking header analysis helper | Partial, not wired into `main.py` |

### `models/`

Shared mapping and status utilities.

| Module | Responsibility | Status |
|---|---|---|
| `booking_mapping.py` | Convert raw booking rows into sheet-ready rows | Active |
| `status.py` | Centralized import status strings | Active |
| `hotel_metrics.py` | Placeholder module | Empty |

### `output/`

Generated artifacts from local runs.

- Rendered page images go under `output/pages/`.
- Extracted JSON files are saved here by the module `__main__` blocks and `main.py`.

### `prompts/`

Prompt templates passed to OpenAI Vision. Each report type has its own prompt file.

### `samples/`

Local input files used by the repo entry point and standalone extractor scripts.

### `services/`

Infrastructure helpers shared across extractors and writers.

| Module | Responsibility | Status |
|---|---|---|
| `pdf_service.py` | Render PDF pages to PNG using PyMuPDF | Active |
| `vision_service.py` | Send images to OpenAI Vision and clean JSON responses | Active |
| `report_detector.py` | Classify report type by file name | Active |

### `validators/`

Validation rules for extracted data.

| Module | Responsibility | Status |
|---|---|---|
| `revenue_validator.py` | Validate revenue extraction payloads | Active |
| `booking_validator.py` | Validate mapped booking rows | Active |

### `writers/`

Google Sheets write helpers and duplicate detection.

| Module | Responsibility | Status |
|---|---|---|
| `google_sheets.py` | Authenticate, append rows, prevent duplicates | Active |

### `venv/`

Local Python environment. Use it when running the project locally if it is present.

## Important Python Modules

### `main.py`

`main.py` is the runtime orchestrator. It chooses the pipeline based on the input file name, routes to the correct extractor, handles booking mapping and validation, and then writes the results to Google Sheets.

### `services/pdf_service.py`

Converts a PDF page to a PNG image using `fitz` / PyMuPDF. The image is written to `output/pages/`.

### `services/vision_service.py`

Encodes page images as base64, calls the OpenAI Responses API with `gpt-4.1-mini`, and parses the returned text into JSON.

### `services/report_detector.py`

Detects report type using the file name only:

- File name contains `revenue report` -> `REVENUE_REPORT`
- File name contains `booking stats` -> `BOOKING_STATS_REPORT`
- Otherwise -> `UNKNOWN`

### `extractors/revenue_report.py`

Processes the first page of the revenue PDF, merges in source metadata, runs revenue validation, and returns a single JSON object for downstream use.

### `extractors/booking_stats.py`

Processes the first 3 pages of the booking PDF, merges page-level raw rows into a single payload, and returns raw extraction data only.

### `extractors/booking_header_analyzer.py`

Standalone helper for extracting header metadata from the booking report. It writes JSON to `output/booking_header_analysis.json` and is not used by `main.py`.

### `models/booking_mapping.py`

Maps each raw booking row into the schema required by `Booking_Forecast`. It uses the `BOOKING_COLUMNS` order to assign values.

### `models/status.py`

Centralized status constants for import and logging states.

### `validators/revenue_validator.py`

Checks revenue payload completeness and validates selected arithmetic relationships.

### `validators/booking_validator.py`

Checks mapped booking rows for presence, duplicate keys, and simple range/negative-value issues.

### `writers/google_sheets.py`

Handles Google OAuth, sheet lookup, row appends, duplicate prevention, and import logging.

## How `main.py` Orchestrates the Pipeline

```text
input PDF path
      |
      v
report_detector.detect_report_type()
      |
      +--> REVENUE_REPORT --> extract_revenue_report()
      |                         |
      |                         v
      |                   revenue_validator
      |                         |
      |                         v
      |                  Daily_Hotel_Metrics
      |                         |
      |                         v
      |                     Import_Log
      |
      +--> BOOKING_STATS_REPORT --> extract_booking_stats()
                                    |
                                    v
                           map_booking_raw_rows()
                                    |
                                    v
                       validate_mapped_booking_rows()
                                    |
                                    v
                        append_booking_forecast_rows()
                                    |
                                    v
                                 Import_Log
```

## Data Flow Diagrams

### Revenue Report

```text
PDF
  -> page 1 PNG
  -> OpenAI Vision prompt
  -> revenue JSON
  -> revenue validator
  -> Google Sheet: Daily_Hotel_Metrics
  -> Google Sheet: Import_Log
```

### Booking Stats Report

```text
PDF
  -> page 1..3 PNGs
  -> OpenAI Vision prompt
  -> raw rows
  -> booking mapping
  -> mapped rows
  -> booking validator
  -> batch append to Google Sheet: Booking_Forecast
  -> Google Sheet: Import_Log
```

## Current State Notes

- `README.md` is currently empty.
- `requirements.txt` is currently empty.
- `config/settings.py` and `models/hotel_metrics.py` are currently empty placeholders.
- `extractors/booking_header_analyzer.py` is present but not part of the orchestrated runtime path.
