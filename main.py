import json
from pathlib import Path

from extractors.revenue_report import extract_revenue_report
from writers.google_sheets import append_daily_hotel_metrics, append_import_log


PDF_PATH = Path("samples/REVENUE REPORT - JUNE 29 2026.pdf")
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


if __name__ == "__main__":
    process_revenue_report(PDF_PATH)