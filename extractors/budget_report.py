import calendar
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from models.status import ImportStatus
from services.pdf_service import pdf_page_to_png
from services.vision_service import extract_json_from_image
from validators.budget_validator import validate_budget_rows
from writers.google_sheets import append_budget_monthly, append_import_log


PDF_PATH = Path("samples/data/HIEX Halifax FULL Budget 2026_Revised (3).pdf")
PROMPT_PATH = Path("prompts/budget_prompt.txt")
HOTELS_PATH = Path("config/hotels.json")
OUTPUT_JSON_PATH = Path("output/budget_report_extracted.json")
REPORT_TYPE = "Budget Report"
BUDGET_PAGE_NUMBER = 1
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
MONTHS_BY_NUMBER = {index: calendar.month_name[index] for index in range(1, 13)}
MONTH_NUMBERS_BY_NAME = {
    calendar.month_name[index].lower(): index for index in range(1, 13)
}


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def canonicalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


@lru_cache(maxsize=1)
def load_hotel_registry() -> list[dict]:
    payload = json.loads(HOTELS_PATH.read_text(encoding="utf-8-sig"))

    if not isinstance(payload, dict):
        raise ValueError(f"Invalid hotel registry structure in {HOTELS_PATH}")

    registry = []

    for canonical_name, metadata in payload.items():
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            continue

        if not isinstance(metadata, dict):
            continue

        normalized_name = canonicalize_text(canonical_name)
        tokens = tuple(normalized_name.split())

        registry.append(
            {
                "canonical_name": canonical_name.strip(),
                "normalized_name": normalized_name,
                "tokens": tokens,
            }
        )

    registry.sort(key=lambda item: len(item["tokens"]), reverse=True)

    if not registry:
        raise ValueError(f"No valid hotel names found in {HOTELS_PATH}")

    return registry


def normalize_hotel_name(raw_hotel_name: str | None) -> str | None:
    if raw_hotel_name is None:
        return None

    raw_name = str(raw_hotel_name).strip()
    if not raw_name:
        return None

    normalized_raw = canonicalize_text(raw_name)
    raw_tokens = set(normalized_raw.split())

    for hotel in load_hotel_registry():
        canonical_name = hotel["canonical_name"]
        canonical_tokens = set(hotel["tokens"])
        canonical_norm = hotel["normalized_name"]

        if normalized_raw == canonical_norm:
            return canonical_name

        if canonical_norm in normalized_raw or normalized_raw in canonical_norm:
            return canonical_name

        if canonical_tokens.issubset(raw_tokens):
            return canonical_name

    return raw_name


def render_budget_page(pdf_path: Path, page_number: int) -> Path:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_pdf_path = Path(temp_dir) / f"{pdf_path.stem}_{page_number + 1}_{uuid4().hex[:8]}.pdf"
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


def coerce_month_number(value, month_name=None):
    normalized_value = normalize_number(value)

    if isinstance(normalized_value, int) and 1 <= normalized_value <= 12:
        return normalized_value

    if isinstance(normalized_value, float) and normalized_value.is_integer():
        integer_value = int(normalized_value)
        if 1 <= integer_value <= 12:
            return integer_value

    if isinstance(value, str):
        normalized_text = canonicalize_text(value)

        for month_name_text, month_number in MONTH_NUMBERS_BY_NAME.items():
            if normalized_text == month_name_text or normalized_text.startswith(month_name_text[:3]):
                return month_number

    if isinstance(month_name, str):
        normalized_text = canonicalize_text(month_name)

        for month_name_text, month_number in MONTH_NUMBERS_BY_NAME.items():
            if normalized_text == month_name_text or normalized_text.startswith(month_name_text[:3]):
                return month_number

    return normalized_value


def normalize_budget_row(row: dict, source_hotel_name: str | None, year) -> dict:
    normalized_row = dict(row)

    normalized_row["hotel_name"] = normalize_hotel_name(source_hotel_name)
    normalized_row["year"] = normalize_number(year)

    for field in MONTHLY_NUMERIC_FIELDS:
        normalized_row[field] = normalize_number(normalized_row.get(field))

    normalized_row["month_number"] = coerce_month_number(
        normalized_row.get("month_number"),
        normalized_row.get("month_name"),
    )

    month_number = normalized_row.get("month_number")
    if isinstance(month_number, int) and 1 <= month_number <= 12:
        normalized_row["month_name"] = MONTHS_BY_NUMBER[month_number]
    elif isinstance(normalized_row.get("month_name"), str):
        normalized_row["month_name"] = normalized_row["month_name"].strip().title()

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

    deduplicated_rows.sort(key=lambda row: row.get("month_number") or 0)
    return deduplicated_rows


def extract_budget_report(pdf_path: Path) -> dict:
    prompt = load_prompt()
    image_path = render_budget_page(pdf_path, page_number=BUDGET_PAGE_NUMBER)
    page_data = extract_json_from_image(image_path, prompt)

    raw_result = {
        "hotel_name": normalize_hotel_name(page_data.get("hotel_name")),
        "year": normalize_number(page_data.get("year")),
        "report_type": REPORT_TYPE,
        "budget_rows": [],
        "source_file_name": pdf_path.name,
        "import_time": datetime.now().isoformat(timespec="seconds"),
    }

    rows = page_data.get("budget_rows")
    if isinstance(rows, list):
        raw_result["budget_rows"] = [
            normalize_budget_row(row, page_data.get("hotel_name"), raw_result["year"])
            for row in rows
            if isinstance(row, dict)
        ]

    raw_result["budget_rows"] = deduplicate_budget_rows(raw_result["budget_rows"])
    return raw_result


def prepare_budget_rows(raw_result: dict) -> list[dict]:
    prepared_rows = []

    for row in raw_result.get("budget_rows", []):
        prepared_row = {
            "hotel_name": row.get("hotel_name", raw_result.get("hotel_name")),
            "year": row.get("year", raw_result.get("year")),
            "month_number": row.get("month_number"),
            "month_name": row.get("month_name"),
            "available_rooms": row.get("available_rooms"),
            "rooms_sold": row.get("rooms_sold"),
            "occupancy_pct": row.get("occupancy_pct"),
            "adr": row.get("adr"),
            "revpar": row.get("revpar"),
            "room_revenue": row.get("room_revenue"),
            "fb_revenue": row.get("fb_revenue"),
            "misc_revenue": row.get("misc_revenue"),
            "total_revenue": row.get("total_revenue"),
            "source_file_name": raw_result.get("source_file_name"),
            "import_time": raw_result.get("import_time"),
            "status": ImportStatus.VALIDATED,
            "notes": "",
        }
        prepared_rows.append(prepared_row)

    return prepared_rows


def safe_append_import_log(data: dict, action: str) -> bool:
    try:
        append_import_log(data, action=action)
        return True
    except Exception as exc:
        print(f"Failed to write Import_Log entry: {exc}")
        return False


def resolve_input_files(argv: list[str]) -> list[Path]:
    if not argv:
        return [PDF_PATH]

    input_files = []

    for argument in argv:
        candidate = Path(argument)

        if candidate.exists():
            input_files.append(candidate)
            continue

        samples_data_candidate = Path("samples/data") / candidate.name
        if samples_data_candidate.exists():
            input_files.append(samples_data_candidate)
            continue

        samples_candidate = Path("samples") / candidate.name
        if samples_candidate.exists():
            input_files.append(samples_candidate)
            continue

        input_files.append(candidate)

    missing_files = [path for path in input_files if not path.exists()]

    if missing_files:
        for path in missing_files:
            print(f"File not found: {path}")
        raise SystemExit(1)

    return input_files


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

    if len(budget_rows) != 12:
        safe_append_import_log(
            {
                "import_time": raw_result.get("import_time"),
                "hotel_name": raw_result.get("hotel_name"),
                "report_type": raw_result.get("report_type"),
                "source_file_name": raw_result.get("source_file_name"),
                "status": ImportStatus.VALIDATION_FAILED,
                "notes": f"Expected 12 budget months, found {len(budget_rows)}.",
            },
            action=ImportStatus.VALIDATION_FAILED,
        )
        print("Budget validation failed.")
        print(f"- Expected 12 budget months, found {len(budget_rows)}.")
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

    validated_result = dict(raw_result)
    validated_result["budget_rows"] = budget_rows
    validated_result["status"] = ImportStatus.VALIDATED
    validated_result["notes"] = ""

    print(json.dumps(validated_result, indent=4))

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
    for file_path in resolve_input_files(sys.argv[1:]):
        process_budget_report(file_path)
