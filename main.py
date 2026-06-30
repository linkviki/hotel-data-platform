import json
from pathlib import Path

from extractors.revenue_report import extract_revenue_report
from writers.google_sheets import append_daily_hotel_metrics, append_import_log, append_booking_forecast_rows
from extractors.booking_stats import extract_booking_stats
from models.booking_mapping import map_booking_raw_rows


PDF_PATH = Path("samples/REVENUE REPORT - JUNE 29 2026.pdf")
BOOKING_PDF_PATH = Path("samples/BOOKING STATS REPORT - JUNE 29 2026.pdf")
OUTPUT_JSON_PATH = Path("output/revenue_report_extracted.json")


def process_revenue_report(pdf_path: Path):
    result = extract_revenue_report(pdf_path)

    print(json.dumps(result, indent=4))

    if result["status"] == "VALIDATED":
        appended = append_daily_hotel_metrics(result)

        if appended:
            append_import_log(result, action="APPENDED")
            print("Appended row to Google Sheet.")
        else:
            append_import_log(result, action="DUPLICATE_SKIPPED")
            print("Skipped Google Sheet append.")
    else:
        append_import_log(result, action="VALIDATION_FAILED")
        print("Validation failed. Logged to Import_Log.")

    OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(f"\nSaved JSON to: {OUTPUT_JSON_PATH}")

def process_booking_stats(pdf_path: Path):
    raw_result = extract_booking_stats(pdf_path)

    print(json.dumps(raw_result, indent=4))

    if raw_result["status"] != "RAW_EXTRACTED":
        append_import_log(raw_result, action="BOOKING_RAW_EXTRACTION_FAILED")
        print("Booking extraction failed.")
        return

    mapped_rows = map_booking_raw_rows(raw_result)

    result = append_booking_forecast_rows(mapped_rows)

    append_import_log(
        {
            "import_time": raw_result.get("import_time"),
            "hotel_name": raw_result.get("hotel_name"),
            "report_type": raw_result.get("report_type"),
            "business_date": raw_result.get("report_date"),
            "source_file_name": raw_result.get("source_file_name"),
            "status": "MAPPED",
            "notes": f"Appended: {result['appended']}, Skipped: {result['skipped']}",
        },
        action="BOOKING_FORECAST_IMPORTED",
    )

    print(f"Booking Forecast appended: {result['appended']}")
    print(f"Booking Forecast skipped: {result['skipped']}")


if __name__ == "__main__":
    process_revenue_report(PDF_PATH)
    process_booking_stats(BOOKING_PDF_PATH)