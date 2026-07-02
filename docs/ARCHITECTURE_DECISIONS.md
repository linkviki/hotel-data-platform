# Architecture Decisions

This file records the current architectural choices visible in the repository. Each note is written in ADR style: context, decision, and consequence.

## ADR-001: Separate Google Sheet Tabs for Revenue and Booking Data

**Status:** Accepted

**Context**

The repository handles two different report families with different row shapes and duplicate keys.

**Decision**

Revenue data is written to `Daily_Hotel_Metrics`, while booking data is written to `Booking_Forecast`.

**Consequences**

- Each tab can keep its own schema.
- Duplicate detection can use report-specific keys.
- Downstream users can consume revenue and booking data independently.

## ADR-002: Booking Stats Extract Raw Rows Before Mapping

**Status:** Accepted

**Context**

The booking report contains repeated row values that must be preserved exactly as extracted before any reshaping.

**Decision**

`extractors/booking_stats.py` returns raw rows and top-level metadata only. Mapping happens later in `models/booking_mapping.py`.

**Consequences**

- The extractor stays close to the source document.
- Mapping rules are isolated from OCR/extraction concerns.
- Validation can run on the mapped sheet-ready structure instead of the raw source shape.

## ADR-003: `main.py` Is the Orchestrator

**Status:** Accepted

**Context**

The repository needs one place to route files, coordinate validation, and trigger writes.

**Decision**

`main.py` detects the report type, calls the correct extractor, coordinates booking mapping and validation, and writes import logs.

**Consequences**

- The top-level flow is easy to follow.
- Report-specific modules stay smaller.
- Runtime behavior is concentrated in one entry point.

## ADR-004: Google Sheets Is the MVP Datastore

**Status:** Accepted

**Context**

The project currently needs a simple shared destination that is easy to inspect and append to.

**Decision**

Google Sheets is used as the primary storage target instead of a database.

**Consequences**

- The solution is simple to operate.
- Non-technical users can inspect the results directly.
- The system inherits Sheets limits and auth overhead.

## ADR-005: Booking Validation Happens After Mapping

**Status:** Accepted

**Context**

The booking extractor returns raw row values in report order, but validation needs sheet-ready fields.

**Decision**

`main.py` maps raw booking rows first and then validates the mapped rows with `validate_mapped_booking_rows()`.

**Consequences**

- Validation can check the actual fields that will be written.
- Mapping errors are easier to diagnose.
- The validator can reason about duplicate keys, numeric ranges, and required mapped columns.

## ADR-006: Batch Appends Are Used for `Booking_Forecast`

**Status:** Accepted

**Context**

Booking reports can produce many rows per run, and per-row sheet writes are inefficient.

**Decision**

`writers/google_sheets.py` batches booking inserts with `append_rows()`.

**Consequences**

- Fewer network calls.
- Faster booking imports.
- Easier to keep a single append pass after duplicate filtering.

## ADR-007: AI Vision Is Used for Image-Based PDFs

**Status:** Accepted

**Context**

The source files are PDFs that are rendered to images before extraction.

**Decision**

The repository uses OpenAI Vision through `services/vision_service.py` to extract JSON from rendered page images.

**Consequences**

- Layout-heavy PDFs can be processed without a bespoke parser for every format.
- Prompt design becomes part of the extraction contract.
- The pipeline depends on OpenAI API availability and image rendering quality.

## ADR-008: Extractors Do Not Write Directly to Google Sheets

**Status:** Accepted

**Context**

The extractor layer should be focused on reading and structuring source data.

**Decision**

Extractors return data; `main.py` and `writers/google_sheets.py` handle persistence.

**Consequences**

- The code is easier to test and reason about.
- Google Sheets auth remains centralized.
- Persistence logic does not leak into OCR/extraction code.

## ADR-009: File-Name Heuristics Are Used for Report Detection

**Status:** Accepted

**Context**

The current sample inputs are named consistently enough to route by file name.

**Decision**

`services/report_detector.py` determines report type from the file name string.

**Consequences**

- Routing is simple and fast.
- The system is sensitive to naming conventions.
- A new input naming scheme will require detector updates.

## ADR-010: Shared Status Strings Are Centralized

**Status:** Accepted

**Context**

The code uses repeated status labels across extractors, validators, writers, and import logs.

**Decision**

`models/status.py` stores shared status constants such as `VALIDATED`, `VALIDATION_FAILED`, `EXTRACTION_FAILED`, `IMPORTED`, `DUPLICATE_SKIPPED`, `MAPPED`, and `VALIDATED_AND_MAPPED`.

**Consequences**

- Status values remain consistent across modules.
- Logging and console output can reuse the same vocabulary.
- Future status additions have one obvious home.
