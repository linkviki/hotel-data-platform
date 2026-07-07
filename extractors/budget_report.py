import calendar
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from models.status import ImportStatus
from services.pdf_service import pdf_page_to_png
from services.vision_service import extract_json_from_image
from validators.budget_validator import validate_budget_rows
from writers.google_sheets import append_budget_monthly, append_import_log


PDF_PATH = Path("samples/data/HIEX Halifax FULL Budget 2026_Revised (3).pdf")
PROMPT_PATH = Path("prompts/budget_prompt.txt")
OUTPUT_JSON_PATH = Path("output/budget_report_extracted.json")
REPORT_TYPE = "Budget Report"
MONTHLY_NUMERIC_FIELDS = [
    "available_rooms",
    "rooms_sold",
    "occupancy_pct",
    "adr",
    "revpar",
    "room_revenue",
    "fb_revenue",
    "misc_revenue",
    "total_revenue",
]


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def render_budget_page(pdf_path: Path, page_number: int) -> Path:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_path = Path(temp_dir) / f"{pdf_path.stem}_{page_number + 1}.pdf"
        shutil.copyfile(pdf_path, temp_pdf_path)
        return pdf_page_to_png(temp_pdf_path, page_number=page_number, zoom=4)


def normalize_number(value):
    if value is None or isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        if cleaned.endswith("%"):
            cleaned = cleaned[:-1].strip()

        if not cleaned:
            return None

        try:
            number = float(cleaned)
        except ValueError:
            return value

        if number.is_integer():
            return int(number)

        return number

    return value


def normalize_budget_row(row: dict, hotel_name: str | None, year) -> dict:
    normalized_row = dict(row)

    normalized_row["hotel_name"] = hotel_name
    normalized_row["year"] = normalize_number(year)

    for field in MONTHLY_NUMERIC_FIELDS:
        normalized_row[field] = normalize_number(normalized_row.get(field))

    normalized_row["month_number"] = normalize_number(normalized_row.get("month_number"))

    month_number = normalized_row.get("month_number")
    month_name = normalized_row.get("month_name")

    if isinstance(month_name, str) and month_name.strip():
        normalized_row["month_name"] = month_name.strip().title()
    elif isinstance(month_number, int) and 1 <= month_number <= 12:
        normalized_row["month_name"] = calendar.month_name[month_number]
    else:
        normalized_row["month_name"] = month_name

    return normalized_row


def deduplicate_budget_rows(rows: list[dict]) -> list[dict]:
    deduplicated_rows = []
    seen_months = set()

    for row in rows:
        month_number = row.get("month_number")
        if month_number in seen_months:
            continue

        seen_months.add(month_number)
        deduplicated_rows.append(row)

    return deduplicated_rows


def extract_budget_report(pdf_path: Path) -> dict:
    prompt = load_prompt()

    result = {
        "hotel_name": None,
        "year": None,
        "report_type": REPORT_TYPE,
        "budget_rows": [],
    }

    for page_number in range(2):
        image_path = render_budget_page(pdf_path, page_number=page_number)
        page_data = extract_json_from_image(image_path, prompt)

        if not result.get("hotel_name") and page_data.get("hotel_name"):
            result["hotel_name"] = page_data.get("hotel_name")

        if result.get("year") is None and page_data.get("year") is not None:
            result["year"] = page_data.get("year")

        rows = page_data.get("budget_rows")
        if isinstance(rows, list):
            result["budget_rows"].extend(rows)

    result["budget_rows"] = deduplicate_budget_rows(
        [
            normalize_budget_row(row, result.get("hotel_name"), result.get("year"))
            for row in result["budget_rows"]
            if isinstance(row, dict)
        ]
    )

    result["source_file_name"] = pdf_path.name
    result["import_time"] = datetime.now().isoformat(timespec="seconds")
    return result


def prepare_budget_rows(raw_result: dict) -> list[dict]:
    prepared_rows = []

    for row in raw_result.get("budget_rows", []):
        prepared_row = dict(row)
        prepared_row["status"] = ImportStatus.VALIDATED
        prepared_row["notes"] = ""
        prepared_row["source_file_name"] = raw_result.get("source_file_name")
        prepared_row["import_time"] = raw_result.get("import_time")
        prepared_rows.append(prepared_row)

    return prepared_rows


def safe_append_import_log(data: dict, action: str) -> bool:
    try:
        append_import_log(data, action=action)
        return True
    except Exception as exc:
        print(f"Failed to write Import_Log entry: {exc}")
        return False


def process_budget_report(pdf_path: Path):
    try:
        raw_result = extract_budget_report(pdf_path)
    except Exception as exc:
        failure_data = {
            "import_time": datetime.now().isoformat(timespec="seconds"),
            "hotel_name": None,
            "report_type": REPORT_TYPE,
            "source_file_name": pdf_path.name,
            "status": ImportStatus.EXTRACTION_FAILED,
            "notes": str(exc),
        }

        safe_append_import_log(failure_data, action=ImportStatus.EXTRACTION_FAILED)
        print("Budget extraction failed.")
        print(f"- {exc}")
        return

    result_for_output = dict(raw_result)
    result_for_output["status"] = ImportStatus.RAW_EXTRACTED
    result_for_output["notes"] = "Raw budget extraction only. Validation and import run separately."

    print(json.dumps(result_for_output, indent=4))

    OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(result_for_output, file, indent=4)

    print(f"\nSaved JSON to: {OUTPUT_JSON_PATH}")

    budget_rows = prepare_budget_rows(raw_result)

    if not budget_rows:
        safe_append_import_log(
            {
                "import_time": raw_result.get("import_time"),
                "hotel_name": raw_result.get("hotel_name"),
                "report_type": raw_result.get("report_type"),
                "source_file_name": raw_result.get("source_file_name"),
                "status": ImportStatus.EXTRACTION_FAILED,
                "notes": "No budget rows extracted.",
            },
            action=ImportStatus.EXTRACTION_FAILED,
        )
        print("Budget extraction failed.")
        return

    validation_errors = validate_budget_rows(budget_rows)

    if validation_errors:
        safe_append_import_log(
            {
                "import_time": raw_result.get("import_time"),
                "hotel_name": raw_result.get("hotel_name"),
                "report_type": raw_result.get("report_type"),
                "source_file_name": raw_result.get("source_file_name"),
                "status": ImportStatus.VALIDATION_FAILED,
                "notes": "; ".join(validation_errors[:10]),
            },
            action=ImportStatus.VALIDATION_FAILED,
        )

        print("Budget validation failed.")
        for error in validation_errors[:10]:
            print(f"- {error}")

        return

    result = append_budget_monthly(budget_rows)

    action = ImportStatus.IMPORTED if result["appended"] else ImportStatus.DUPLICATE_SKIPPED
    status = ImportStatus.VALIDATED if result["appended"] else ImportStatus.DUPLICATE_SKIPPED

    safe_append_import_log(
        {
            "import_time": raw_result.get("import_time"),
            "hotel_name": raw_result.get("hotel_name"),
            "report_type": raw_result.get("report_type"),
            "status": status,
            "notes": f"Appended: {result['appended']}, Skipped: {result['skipped']}",
        },
        action=action,
    )

    print(f"Budget Monthly appended: {result['appended']}")
    print(f"Budget Monthly skipped: {result['skipped']}")


if __name__ == "__main__":
    process_budget_report(PDF_PATH)
