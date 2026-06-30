import json
from pathlib import Path

from extractors.revenue_report import extract_revenue_report
from writers.google_sheets import append_daily_hotel_metrics, append_import_log, append_booking_forecast_rows
from extractors.booking_stats import extract_booking_stats
from models.booking_mapping import map_booking_raw_rows
from models.status import ImportStatus
from services.report_detector import detect_report_type
from validators.booking_validator import validate_mapped_booking_rows


PDF_PATH = Path("samples/REVENUE REPORT - JUNE 29 2026.pdf")
BOOKING_PDF_PATH = Path("samples/BOOKING STATS REPORT - JUNE 29 2026.pdf")
OUTPUT_JSON_PATH = Path("output/revenue_report_extracted.json")


def process_revenue_report(pdf_path: Path):
    result = extract_revenue_report(pdf_path)

    print(json.dumps(result, indent=4))

    if result["status"] == ImportStatus.VALIDATED:
        appended = append_daily_hotel_metrics(result)

        if appended:
            append_import_log(result, action=ImportStatus.IMPORTED)
            print("Appended row to Google Sheet.")
        else:
            append_import_log(result, action=ImportStatus.DUPLICATE_SKIPPED)
            print("Skipped Google Sheet append.")
    else:
        append_import_log(result, action=ImportStatus.VALIDATION_FAILED)
        print("Validation failed. Logged to Import_Log.")

    OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(f"\nSaved JSON to: {OUTPUT_JSON_PATH}")

def process_booking_stats(pdf_path: Path):
    raw_result = extract_booking_stats(pdf_path)

    print(json.dumps(raw_result, indent=4))

    raw_rows = raw_result.get("raw_rows")

    if not raw_rows:
        append_import_log(
            {
                "import_time": raw_result.get("import_time"),
                "hotel_name": raw_result.get("hotel_name"),
                "report_type": raw_result.get("report_type"),
                "business_date": raw_result.get("report_date"),
                "source_file_name": raw_result.get("source_file_name"),
                "status": ImportStatus.EXTRACTION_FAILED,
                "notes": "No booking rows extracted.",
            },
            action=ImportStatus.EXTRACTION_FAILED,
        )
        print("Booking extraction failed.")
        return

    mapped_rows = map_booking_raw_rows(raw_result)

    validation_errors = validate_mapped_booking_rows(mapped_rows)

    if validation_errors:
        append_import_log(
            {
                "import_time": raw_result.get("import_time"),
                "hotel_name": raw_result.get("hotel_name"),
                "report_type": raw_result.get("report_type"),
                "business_date": raw_result.get("report_date"),
                "source_file_name": raw_result.get("source_file_name"),
                "status": ImportStatus.VALIDATION_FAILED,
                "notes": "; ".join(validation_errors[:10]),
            },
            action=ImportStatus.VALIDATION_FAILED,
        )

        print("Booking validation failed.")
        for error in validation_errors[:10]:
            print(f"- {error}")

        return

    validated_result = dict(raw_result)
    validated_result["status"] = ImportStatus.VALIDATED_AND_MAPPED
    validated_result["notes"] = ""
    print(json.dumps(validated_result, indent=4))

    result = append_booking_forecast_rows(mapped_rows)

    append_import_log(
        {
            "import_time": raw_result.get("import_time"),
            "hotel_name": raw_result.get("hotel_name"),
            "report_type": raw_result.get("report_type"),
            "business_date": raw_result.get("report_date"),
            "source_file_name": raw_result.get("source_file_name"),
            "status": ImportStatus.VALIDATED_AND_MAPPED,
            "notes": f"Appended: {result['appended']}, Skipped: {result['skipped']}",
        },
        action=ImportStatus.IMPORTED,
    )

    print(f"Booking Forecast appended: {result['appended']}")
    print(f"Booking Forecast skipped: {result['skipped']}")

def process_file(pdf_path: Path):
    report_type = detect_report_type(pdf_path)

    if report_type == "REVENUE_REPORT":
        process_revenue_report(pdf_path)

    elif report_type == "BOOKING_STATS_REPORT":
        process_booking_stats(pdf_path)

    else:
        print(f"Unknown report type: {pdf_path.name}")


if __name__ == "__main__":
    sample_files = [
        Path("samples/REVENUE REPORT - JUNE 29 2026.pdf"),
        Path("samples/BOOKING STATS REPORT - JUNE 29 2026.pdf"),
    ]

    for file_path in sample_files:
        process_file(file_path)
