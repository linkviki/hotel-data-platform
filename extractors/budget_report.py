import argparse
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

import pdfplumber

from models.status import ImportStatus
from writers.google_sheets import get_google_sheet
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
SHEET_CLEAR_RANGE = "A2:Z"
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
TABLE_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
    "text_tolerance": 2,
}
PRE_REVENUE_ROW_FIELD_MAP = {
    "available rooms": "available_rooms",
    "rooms sold": "rooms_sold",
    "occupancy": "occupancy_pct",
    "adr": "adr",
    "revpar": "revpar",
}
REVENUE_ROW_FIELD_MAP = {
    "room revenue": "room_revenue",
    "food beverage": "fb_revenue",
    "food and beverage": "fb_revenue",
    "miscellaneous": "misc_revenue",
    "total revenue": "total_revenue",
}


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def canonicalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def extract_budget_year_from_text(page_text: str, file_name: str) -> int | None:
    year_candidates = [
        int(candidate)
        for candidate in re.findall(r"\b(20\d{2})\b", f"{file_name}\n{page_text}")
    ]

    if year_candidates:
        return max(year_candidates)

    return None


def extract_hotel_name_from_text(page_text: str) -> str | None:
    canonical_names = {hotel["canonical_name"] for hotel in load_hotel_registry()}
    normalized_text = canonicalize_text(page_text)
    text_tokens = set(normalized_text.split())

    for line in page_text.splitlines():
        candidate = normalize_hotel_name(line)
        if candidate in canonical_names:
            return candidate

    for hotel in load_hotel_registry():
        if hotel["normalized_name"] in normalized_text:
            return hotel["canonical_name"]

        if set(hotel["tokens"]).issubset(text_tokens):
            return hotel["canonical_name"]

    return None


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


def extract_budget_rows_from_pdf_table(pdf_path: Path) -> dict | None:
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) <= BUDGET_PAGE_NUMBER:
            return None

        page = pdf.pages[BUDGET_PAGE_NUMBER]
        page_text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
        hotel_name = extract_hotel_name_from_text(page_text)
        year = extract_budget_year_from_text(page_text, pdf_path.name)
        table = page.extract_table(table_settings=TABLE_SETTINGS)

    if not hotel_name or year is None or not table:
        return None

    month_rows: dict[str, list] = {}
    in_revenue_section = False

    for raw_row in table:
        if not raw_row or len(raw_row) < 18:
            continue

        label_parts = [
            str(cell).replace("\n", "").strip()
            for cell in raw_row[4:6]
            if isinstance(cell, str) and cell.strip()
        ]

        row_label = canonicalize_text("".join(label_parts))

        if row_label == "revenue":
            in_revenue_section = True
            continue

        if row_label == "cost of sales" and in_revenue_section:
            break

        field_name = None
        if not in_revenue_section:
            field_name = PRE_REVENUE_ROW_FIELD_MAP.get(row_label)
        else:
            field_name = REVENUE_ROW_FIELD_MAP.get(row_label)

        if field_name is None:
            continue

        month_values = [normalize_number(cell) for cell in raw_row[6:18]]
        if len(month_values) != 12:
            continue

        month_rows[field_name] = month_values

    required_fields = set(PRE_REVENUE_ROW_FIELD_MAP.values()) | set(REVENUE_ROW_FIELD_MAP.values())
    if not required_fields.issubset(month_rows):
        return None

    raw_result = {
        "hotel_name": hotel_name,
        "year": year,
        "report_type": REPORT_TYPE,
        "budget_rows": [],
        "source_file_name": pdf_path.name,
        "import_time": datetime.now().isoformat(timespec="seconds"),
    }

    for month_index in range(12):
        month_number = month_index + 1
        raw_result["budget_rows"].append(
            {
                "month_number": month_number,
                "month_name": MONTHS_BY_NUMBER[month_number],
                "available_rooms": month_rows["available_rooms"][month_index],
                "rooms_sold": month_rows["rooms_sold"][month_index],
                "occupancy_pct": month_rows["occupancy_pct"][month_index],
                "adr": month_rows["adr"][month_index],
                "revpar": month_rows["revpar"][month_index],
                "room_revenue": month_rows["room_revenue"][month_index],
                "fb_revenue": month_rows["fb_revenue"][month_index],
                "misc_revenue": month_rows["misc_revenue"][month_index],
                "total_revenue": month_rows["total_revenue"][month_index],
            }
        )

    raw_result["budget_rows"] = deduplicate_budget_rows(
        [
            normalize_budget_row(row, raw_result["hotel_name"], raw_result["year"])
            for row in raw_result["budget_rows"]
        ]
    )
    return raw_result


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
    parsed_result = extract_budget_rows_from_pdf_table(pdf_path)
    if parsed_result is not None:
        return parsed_result

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


def clear_budget_monthly_rows() -> bool:
    try:
        sheet = get_google_sheet()
        worksheet = sheet.worksheet("Budget_Monthly")
        worksheet.batch_clear([SHEET_CLEAR_RANGE])
        return True
    except Exception as exc:
        print(f"Failed to clear Budget_Monthly: {exc}")
        return False


def extract_and_validate_budget_report(pdf_path: Path) -> tuple[dict, list[dict], list[str]]:
    raw_result = extract_budget_report(pdf_path)
    budget_rows = prepare_budget_rows(raw_result)

    validation_errors = []

    if len(budget_rows) != 12:
        validation_errors.append(f"Expected 12 budget months, found {len(budget_rows)}.")
        return raw_result, budget_rows, validation_errors

    validation_errors = validate_budget_rows(budget_rows)
    return raw_result, budget_rows, validation_errors


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


def process_budget_report(pdf_path: Path) -> dict[str, int]:
    try:
        raw_result, budget_rows, validation_errors = extract_and_validate_budget_report(pdf_path)
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
        return {
            "rows_extracted": 0,
            "rows_validated": 0,
            "rows_written": 0,
            "skipped_rows": 0,
        }

    result_for_output = dict(raw_result)
    result_for_output["status"] = ImportStatus.RAW_EXTRACTED
    result_for_output["notes"] = "Raw budget extraction only. Validation and import run separately."

    print(json.dumps(result_for_output, indent=4))

    OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(result_for_output, file, indent=4)

    print(f"\nSaved JSON to: {OUTPUT_JSON_PATH}")

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

        return {
            "rows_extracted": len(budget_rows),
            "rows_validated": 0,
            "rows_written": 0,
            "skipped_rows": len(budget_rows),
        }

    validated_result = dict(raw_result)
    validated_result["budget_rows"] = budget_rows
    validated_result["status"] = ImportStatus.VALIDATED
    validated_result["notes"] = ""

    print(json.dumps(validated_result, indent=4))

    try:
        result = append_budget_monthly(budget_rows)
    except Exception as exc:
        print(f"Budget Monthly write failed: {exc}")
        safe_append_import_log(
            {
                "import_time": raw_result.get("import_time"),
                "hotel_name": raw_result.get("hotel_name"),
                "report_type": raw_result.get("report_type"),
                "source_file_name": raw_result.get("source_file_name"),
                "status": ImportStatus.VALIDATED,
                "notes": f"Budget Monthly write failed: {exc}",
            },
            action=ImportStatus.VALIDATED,
        )
        return {
            "rows_extracted": len(budget_rows),
            "rows_validated": len(budget_rows),
            "rows_written": 0,
            "skipped_rows": 0,
        }

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

    return {
        "rows_extracted": len(budget_rows),
        "rows_validated": len(budget_rows),
        "rows_written": result["appended"],
        "skipped_rows": result["skipped"],
    }


def run_budget_reports(pdf_paths: list[Path], rebuild: bool = False) -> None:
    if rebuild:
        preflight_runs = []
        total_extracted = 0
        total_validated = 0

        for pdf_path in pdf_paths:
            try:
                raw_result, budget_rows, validation_errors = extract_and_validate_budget_report(pdf_path)
            except Exception as exc:
                print("Budget extraction failed.")
                print(f"- {exc}")
                print(f"rows extracted: {total_extracted}")
                print(f"rows validated: {total_validated}")
                print("rows written: 0")
                print(f"skipped rows: {total_extracted - total_validated}")
                return

            total_extracted += len(budget_rows)

            if validation_errors:
                result_for_output = dict(raw_result)
                result_for_output["status"] = ImportStatus.RAW_EXTRACTED
                result_for_output["notes"] = "Raw budget extraction only. Validation and import run separately."
                print(json.dumps(result_for_output, indent=4))
                OUTPUT_JSON_PATH.parent.mkdir(exist_ok=True)
                with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as file:
                    json.dump(result_for_output, file, indent=4)
                print(f"\nSaved JSON to: {OUTPUT_JSON_PATH}")
                print("Budget validation failed.")
                for error in validation_errors[:10]:
                    print(f"- {error}")
                print(f"rows extracted: {total_extracted}")
                print(f"rows validated: {total_validated}")
                print("rows written: 0")
                print(f"skipped rows: {total_extracted - total_validated}")
                return

            total_validated += len(budget_rows)
            preflight_runs.append(pdf_path)

        if not clear_budget_monthly_rows():
            print(f"rows extracted: {total_extracted}")
            print(f"rows validated: {total_validated}")
            print("rows written: 0")
            print(f"skipped rows: {total_extracted - total_validated}")
            return

        total_written = 0
        total_skipped = 0

        for pdf_path in preflight_runs:
            result = process_budget_report(pdf_path)
            total_written += result.get("rows_written", 0)
            total_skipped += result.get("skipped_rows", 0)

        print(f"rows extracted: {total_extracted}")
        print(f"rows validated: {total_validated}")
        print(f"rows written: {total_written}")
        print(f"skipped rows: {total_skipped}")
        return

    total_extracted = 0
    total_validated = 0
    total_written = 0
    total_skipped = 0

    for pdf_path in pdf_paths:
        result = process_budget_report(pdf_path)
        total_extracted += result.get("rows_extracted", 0)
        total_validated += result.get("rows_validated", 0)
        total_written += result.get("rows_written", 0)
        total_skipped += result.get("skipped_rows", 0)

    print(f"rows extracted: {total_extracted}")
    print(f"rows validated: {total_validated}")
    print(f"rows written: {total_written}")
    print(f"skipped rows: {total_skipped}")


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(description="Extract budget PDFs into Budget_Monthly.")
    parser.add_argument("--rebuild", action="store_true", help="Clear Budget_Monthly before writing.")
    parser.add_argument("pdf_paths", nargs="*", help="Budget PDF file paths.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    arguments = parse_args(sys.argv[1:])
    file_paths = resolve_input_files(arguments.pdf_paths)
    run_budget_reports(file_paths, rebuild=arguments.rebuild)
