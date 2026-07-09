from pathlib import Path
from datetime import datetime

from services.date_utils import parse_date_value
from services.pdf_service import pdf_page_to_png
from services.hotel_normalization import resolve_hotel_name
from services.vision_service import extract_json_from_image
from models.status import ImportStatus
from validators.revenue_validator import validate_revenue_report

PDF_PATH = Path("samples/REVENUE REPORT - JUNE 29 2026.pdf")
PROMPT_PATH = Path("prompts/revenue_report_prompt.txt")
OUTPUT_JSON_PATH = Path("output/revenue_report_extracted.json")


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _normalize_business_date(raw_value, import_time: str) -> str | None:
    parsed_date = parse_date_value(raw_value)
    if parsed_date is None:
        return raw_value

    import_year = datetime.fromisoformat(import_time).year

    if parsed_date.year < 2010:
        return parsed_date.replace(year=import_year).isoformat()

    return parsed_date.isoformat()


def extract_revenue_report(pdf_path: Path) -> dict:
    image_path = pdf_page_to_png(pdf_path, page_number=0)
    prompt = load_prompt()

    data = extract_json_from_image(image_path, prompt)
    resolution = resolve_hotel_name(data.get("hotel_name"), fallback_candidates=[pdf_path.stem])

    data["source_file_name"] = pdf_path.name
    data["source_email_subject"] = None
    data["source_email_sender"] = None
    data["raw_hotel_name"] = resolution["raw_hotel_name"]
    data["hotel_name"] = resolution["normalized_hotel_name"]
    data["hotel_name_resolution_source"] = resolution["resolved_from"]
    data["import_time"] = datetime.now().isoformat(timespec="seconds")
    data["business_date"] = _normalize_business_date(data.get("business_date"), data["import_time"])

    print(
        "Revenue hotel resolution: "
        f"raw={data.get('raw_hotel_name')!r}, "
        f"normalized={data.get('hotel_name')!r}, "
        f"source={data.get('hotel_name_resolution_source')!r}"
    )
    print(
        "Revenue import summary: "
        f"source_file={data.get('source_file_name')!r}, "
        f"business_date={data.get('business_date')!r}, "
        f"import_time={data.get('import_time')!r}, "
        f"rooms_sold={data.get('rooms_sold')!r}, "
        f"occupancy_pct={data.get('occupancy_pct')!r}, "
        f"room_revenue={data.get('room_revenue')!r}, "
        f"gross_revenue={data.get('gross_revenue')!r}"
    )

    errors = validate_revenue_report(data)

    if errors:
        data["status"] = ImportStatus.VALIDATION_FAILED
        data["notes"] = "; ".join(errors)
    else:
        data["status"] = ImportStatus.VALIDATED
        data["notes"] = ""

    return data
