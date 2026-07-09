import json
from datetime import datetime
from pathlib import Path

from services.date_utils import format_date_only
from services.hotel_normalization import resolve_hotel_name
from services.pdf_service import get_pdf_page_count, pdf_page_to_png
from services.vision_service import extract_json_from_image
from models.status import ImportStatus

PDF_PATH = Path("samples/BOOKING STATS REPORT - JUNE 29 2026.pdf")
PROMPT_PATH = Path("prompts/booking_stats_prompt.txt")
OUTPUT_JSON_PATH = Path("output/booking_stats_extracted.json")


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def extract_booking_stats(pdf_path: Path) -> dict:
    prompt = load_prompt()
    import_time = datetime.now().isoformat(timespec="seconds")
    page_count = get_pdf_page_count(pdf_path)

    all_rows = []
    result_header = {
        "hotel_name": None,
        "report_type": "Booking Stats Report",
        "report_date": None,
        "email_received_date": None,
        "received_date": None,
        "message_date": None,
        "raw_rows": [],
    }

    if page_count <= 0:
        raise ValueError(f"Booking Stats PDF has no pages: {pdf_path.name}")

    print(f"Booking Stats PDF: {pdf_path.name}")
    print(f"Booking Stats page_count: {page_count}")
    print(f"Booking Stats page_indexes: {list(range(page_count))}")

    for page_number in range(page_count):
        print(f"Booking Stats processing page {page_number}")
        image_path = pdf_page_to_png(pdf_path, page_number=page_number)
        page_data = extract_json_from_image(image_path, prompt)

        if page_data.get("hotel_name"):
            result_header["hotel_name"] = page_data.get("hotel_name")

        if page_data.get("report_date"):
            result_header["report_date"] = page_data.get("report_date")

        if page_data.get("email_received_date"):
            result_header["email_received_date"] = page_data.get("email_received_date")

        if page_data.get("received_date"):
            result_header["received_date"] = page_data.get("received_date")

        if page_data.get("message_date"):
            result_header["message_date"] = page_data.get("message_date")

        if isinstance(page_data.get("raw_rows"), list):
            all_rows.extend(page_data["raw_rows"])

    resolution = resolve_hotel_name(
        result_header.get("hotel_name"),
        fallback_candidates=[pdf_path.stem],
    )

    result_header["raw_rows"] = all_rows
    result_header["source_file_name"] = pdf_path.name
    result_header["import_time"] = import_time
    result_header["raw_hotel_name"] = resolution["raw_hotel_name"]
    result_header["hotel_name"] = resolution["normalized_hotel_name"]
    result_header["hotel_name_resolution_source"] = resolution["resolved_from"]
    result_header["snapshot_date"] = format_date_only(
        result_header.get("email_received_date")
        or result_header.get("received_date")
        or result_header.get("message_date")
        or result_header.get("report_date")
        or import_time,
        fallback=import_time,
    )

    print(
        "Booking hotel resolution: "
        f"raw={result_header.get('raw_hotel_name')!r}, "
        f"normalized={result_header.get('hotel_name')!r}, "
        f"source={result_header.get('hotel_name_resolution_source')!r}"
    )
    print(f"Booking snapshot_date used: {result_header.get('snapshot_date')}")
    print(f"Booking import_time used: {result_header.get('import_time')}")

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
