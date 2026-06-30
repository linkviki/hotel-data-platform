import json
from pathlib import Path
from datetime import datetime

from services.pdf_service import pdf_page_to_png
from services.vision_service import extract_json_from_image
from models.status import ImportStatus

PDF_PATH = Path("samples/BOOKING STATS REPORT - JUNE 29 2026.pdf")
PROMPT_PATH = Path("prompts/booking_stats_prompt.txt")
OUTPUT_JSON_PATH = Path("output/booking_stats_extracted.json")


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_booking_stats(pdf_path: Path) -> dict:
    prompt = load_prompt()

    all_rows = []
    result_header = {
        "hotel_name": None,
        "report_type": "Booking Stats Report",
        "report_date": None,
        "raw_rows": [],
    }

    # Booking report has multiple pages, so process first 3 pages for now
    for page_number in range(3):
        image_path = pdf_page_to_png(pdf_path, page_number=page_number)
        page_data = extract_json_from_image(image_path, prompt)

        if page_data.get("hotel_name"):
            result_header["hotel_name"] = page_data.get("hotel_name")

        if page_data.get("report_date"):
            result_header["report_date"] = page_data.get("report_date")

        if isinstance(page_data.get("raw_rows"), list):
            all_rows.extend(page_data["raw_rows"])

    result_header["raw_rows"] = all_rows

    result_header["source_file_name"] = pdf_path.name
    result_header["import_time"] = datetime.now().isoformat(timespec="seconds")
    return result_header


if __name__ == "__main__":
    result = extract_booking_stats(PDF_PATH)
    result_for_output = dict(result)
    result_for_output["status"] = ImportStatus.RAW_EXTRACTED
    result_for_output["notes"] = "Raw table extraction only. Mapping not applied yet."

    print(json.dumps(result_for_output, indent=4))

    OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_for_output, f, indent=4)

    print(f"\nSaved JSON to: {OUTPUT_JSON_PATH}")
