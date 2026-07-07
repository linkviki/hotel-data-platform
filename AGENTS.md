# hotel-data-platform

## Project Overview

`hotel-data-platform` is a Python pipeline that extracts data from hotel PDF reports, converts the PDFs to page images, sends those images to OpenAI Vision for JSON extraction, validates the extracted data, and appends results to Google Sheets.

Current report coverage:

| Report Type | Current Path | Current Output |
|---|---|---|
| Revenue Report | `extractors/revenue_report.py` -> `validators/revenue_validator.py` -> `writers/google_sheets.py` | `Daily_Hotel_Metrics` and `Import_Log` |
| Booking Stats Report | `extractors/booking_stats.py` -> `models/booking_mapping.py` -> `validators/booking_validator.py` -> `writers/google_sheets.py` | `Booking_Forecast` and `Import_Log` |
| Booking Header Analysis | `extractors/booking_header_analyzer.py` | `output/booking_header_analysis.json` |

## AI Agent Instructions

- Read the current code before changing anything.
- Keep changes minimal and aligned with the existing module boundaries.
- Do not invent new report types, prompts, sheet tabs, or schemas.
- Prefer small, explicit edits over broad refactors.
- Preserve the current extraction and validation flow unless the user explicitly asks for a behavior change.
- Treat `output/`, `samples/`, `credentials/`, `venv/`, and `__pycache__/` as local/generated areas.
- Use `apply_patch` for file edits.
- Avoid destructive Git operations unless explicitly requested.

## Folder Responsibilities

| Folder | Responsibility | Notes |
|---|---|---|
| `config/` | Configuration placeholders | `config/settings.py` is currently empty. |
| `config/hotels.json` | Canonical hotel registry | Stores standardized hotel names and property metadata. Currently not consumed by a runtime module. |
| `credentials/` | Local Google OAuth files | Contains OAuth client/token material used by the Sheets client. |
| `docs/` | Repository documentation | Human and agent-facing docs live here. |
| `extractors/` | PDF-to-JSON extraction logic | Contains revenue, booking, and booking header extraction helpers. |
| `models/` | Shared row mapping and status constants | `booking_mapping.py` is active; `hotel_metrics.py` is currently empty. |
| `output/` | Generated artifacts | JSON outputs and rendered PDF page images are written here. |
| `prompts/` | OpenAI prompt templates | One prompt per extractor. |
| `samples/` | Local sample inputs | Sample PDFs and sample email text. |
| `services/` | Reusable infrastructure helpers | PDF rendering, OpenAI Vision calls, and report detection. |
| `validators/` | Data quality checks | Revenue validation and mapped booking validation. |
| `writers/` | Google Sheets write helpers | Sheet append and duplicate detection logic. |
| `venv/` | Local Python environment | Use this when available for local execution. |

## Coding Standards

- Keep modules focused on one responsibility.
- Prefer ASCII text in code and docs unless a file already uses non-ASCII.
- Do not change prompts, OAuth setup, or OpenAI integration without approval.
- Do not add inline comments unless they clarify non-obvious logic.
- Keep status strings centralized in `models/status.py`.
- Preserve existing sheet names and duplicate-key rules.
- Do not add business logic to extractors that belongs in validation or mapping.
- Treat `config/hotels.json` as the canonical hotel registry when implementing hotel-name normalization.
- Do not guess a hotel mapping if a source name is not present in `config/hotels.json`; preserve the raw name and flag it for review.

## Hotel Normalization Notes

- `config/hotels.json` is the single source of truth for canonical hotel names and their metadata.
- The current codebase does not yet read this file at runtime; documentation and future implementations should treat it as the contract for normalization work.
- Canonical names are the top-level JSON keys, for example `Residence Inn Laval` and `Holiday Inn Express Halifax`.
- Standardization means converting aliases or report variations to the exact canonical key before any grouping, duplicate detection, dashboard transform, or warehouse-style output.
- Unknown hotels should remain usable as raw source values, but they should not be silently re-labeled or merged into a different hotel.
- When adding a new hotel, add a new top-level key with the canonical name and property metadata, then update any downstream mappings or tests that depend on the registry.
- Main risk of a missing registry entry is fractured reporting: the same property can appear under multiple names, which will break grouping, comparisons, and duplicate checks.

## Current Workflow

### Revenue Report

1. `main.py` detects the report type from the file name.
2. `extractors/revenue_report.py` renders page 1 to PNG and sends the image plus prompt to OpenAI Vision.
3. `validators/revenue_validator.py` checks required fields and basic arithmetic consistency.
4. `writers/google_sheets.py` appends to `Daily_Hotel_Metrics` unless the row is already present.
5. `writers/google_sheets.py` appends an `Import_Log` entry for success, duplicate skip, or validation failure.

### Booking Stats Report

1. `main.py` detects the report type from the file name.
2. `extractors/booking_stats.py` renders the first 3 pages and extracts raw rows only.
3. `models/booking_mapping.py` maps raw row values into sheet-ready fields.
4. `validators/booking_validator.py` validates the mapped rows.
5. `writers/google_sheets.py` batch appends to `Booking_Forecast`.
6. `writers/google_sheets.py` appends an `Import_Log` entry.

### Booking Header Analysis

- `extractors/booking_header_analyzer.py` is a standalone helper that extracts booking header metadata to `output/booking_header_analysis.json`.
- It is not wired into `main.py`.

## What Agents Must Not Change Without Approval

- Google OAuth flow in `writers/google_sheets.py`.
- OpenAI client usage and model choice in `services/vision_service.py`.
- Prompt files in `prompts/`.
- Sheet tab names and column ordering assumptions.
- Report detection rules in `services/report_detector.py`.
- Duplicate-key definitions in `writers/google_sheets.py`.
- Business validation rules unless the user explicitly asks for a behavior change.
- File names and folder names.

## How To Run / Test

### Manual run

Use the project virtual environment when it is available:

```powershell
.\venv\Scripts\python.exe main.py
```

### Required environment

- `OPENAI_API_KEY`
- `GOOGLE_SHEET_ID`
- `GOOGLE_CLIENT_SECRET_FILE`
- `GOOGLE_TOKEN_FILE`

### What to expect

- Revenue output is printed as JSON, then written to `output/revenue_report_extracted.json`.
- Booking output is printed as raw extraction JSON, and a validated booking payload is printed on success.
- Successful booking imports print appended/skipped counts.
- `Import_Log` receives one row per attempt.

### Current test situation

- No automated test suite is currently defined in the repository.
- The current practical verification method is to run `main.py` or the per-module `__main__` blocks.

## Git Workflow

- Check `git status` before editing.
- Assume the working tree may already contain user changes.
- Do not revert files you did not change.
- Keep commits or branch operations out of scope unless explicitly requested.

## Google Sheets Notes

- Authentication uses a local installed-app OAuth flow.
- `TOKEN_FILE` is refreshed or created locally.
- `Daily_Hotel_Metrics` duplicate detection uses `business_date + hotel_name + report_type`.
- `Booking_Forecast` duplicate detection uses `hotel_name + stay_date + source_file_name`.
- `Booking_Forecast` writes use batch `append_rows`.
- `Import_Log` always appends a new row.

## OpenAI Vision Notes

- The pipeline uses `gpt-4.1-mini` through the OpenAI Responses API.
- Images are base64 encoded before being sent to OpenAI.
- JSON is extracted from `response.output_text` after stripping code fences and surrounding text.
- The booking and revenue extractors both rely on prompt files to define the JSON schema.

## Validation Philosophy

- Validate mapped booking rows after mapping, not during raw extraction.
- Validate revenue rows inside the revenue extractor before Google Sheets write.
- Keep validation focused on completeness, duplicates, and obvious range checks.
- Do not force report-specific business formulas unless the report itself requires them.

## Duplicate Detection Strategy

| Target | Duplicate Key | Behavior |
|---|---|---|
| `Daily_Hotel_Metrics` | `business_date`, `hotel_name`, `report_type` | Skip append if a matching record already exists. |
| `Booking_Forecast` | `hotel_name`, `stay_date`, `source_file_name` | Skip append if a matching record already exists, including rows already queued in the same batch. |

## How To Add a New Report Type

1. Add a prompt file under `prompts/`.
2. Add a dedicated extractor under `extractors/`.
3. Add mapping logic under `models/` if the raw extraction needs reshaping.
4. Add validation under `validators/`.
5. Add a write helper under `writers/` if Google Sheets output is needed.
6. Extend `services/report_detector.py` only if the file-name heuristic can reliably identify the new report.
7. Wire the new path into `main.py`.

## Common Mistakes To Avoid

- Writing directly to Google Sheets from extractors.
- Changing prompt schemas without updating the extractor and validator together.
- Assuming booking rows are already mapped when they are still raw.
- Reintroducing business-math checks that the source report does not support.
- Forgetting that `output/` and `samples/` are generated/local and ignored by Git.
- Running against the system Python when the project venv is available.

## Future Roadmap

- Add an automated test suite.
- Populate or remove placeholder modules such as `config/settings.py` and `models/hotel_metrics.py`.
- Decide whether `booking_header_analyzer.py` should become part of the supported workflow.
- Expand report detection beyond filename heuristics if new inputs require it.
- Review whether booking extraction should always stop at the first 3 pages or adapt to report length.
