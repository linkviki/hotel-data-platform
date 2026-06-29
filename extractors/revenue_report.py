import json
from pathlib import Path
from datetime import datetime

from services.pdf_service import pdf_page_to_png
from services.vision_service import extract_json_from_image
from validators.revenue_validator import validate_revenue_report
from writers.google_sheets import append_daily_hotel_metrics, append_import_log

PDF_PATH = Path("samples/REVENUE REPORT - JUNE 29 2026.pdf")
PROMPT_PATH = Path("prompts/revenue_report_prompt.txt")
OUTPUT_JSON_PATH = Path("output/revenue_report_extracted.json")


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_revenue_report(pdf_path: Path) -> dict:
    image_path = pdf_page_to_png(pdf_path, page_number=0)
    prompt = load_prompt()

    data = extract_json_from_image(image_path, prompt)

    data["source_file_name"] = pdf_path.name
    data["source_email_subject"] = None
    data["source_email_sender"] = None
    data["import_time"] = datetime.now().isoformat(timespec="seconds")

    errors = validate_revenue_report(data)

    if errors:
        data["status"] = "VALIDATION_FAILED"
        data["notes"] = "; ".join(errors)
    else:
        data["status"] = "VALIDATED"
        data["notes"] = ""

    return data


if __name__ == "__main__":
    result = extract_revenue_report(PDF_PATH)

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