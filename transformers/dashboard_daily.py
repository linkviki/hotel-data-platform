from __future__ import annotations

import calendar
import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from writers.google_sheets import get_google_sheet


TARGET_TAB = "Dashboard_Daily_Performance"
SOURCE_DAILY_TAB = "Daily_Hotel_Metrics"
SOURCE_FORECAST_TAB = "Booking_Forecast"
HOTELS_PATH = Path("config/hotels.json")

TARGET_COLUMNS = [
    "hotel_name",
    "date",
    "month_number",
    "month_name",
    "data_type",
    "rooms_sold",
    "occupancy_pct",
    "adr",
    "revpar",
    "room_revenue",
    "total_revenue",
    "source_file_name",
    "forecast_snapshot_date",
    "import_time",
]

MONTHS_BY_NUMBER = {index: calendar.month_name[index] for index in range(1, 13)}


def canonicalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def parse_datetime_value(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        normalized_candidate = candidate.replace("Z", "+00:00")
        for pattern in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
        ):
            try:
                return datetime.strptime(candidate, pattern)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(normalized_candidate)
        except ValueError:
            return None

    return None


def parse_date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        for pattern in (
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                return datetime.strptime(candidate, pattern).date()
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
        except ValueError:
            return None

    return None


def parse_number(value: Any):
    if value is None or isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        candidate = value.strip().replace(",", "").replace("$", "").replace("%", "")
        if not candidate:
            return None

        try:
            number = float(candidate)
        except ValueError:
            return value

        if number.is_integer():
            return int(number)

        return number

    return value


def normalize_percentage(value: Any):
    number = parse_number(value)

    if isinstance(number, (int, float)):
        if 0 < abs(number) <= 1:
            return round(number * 100, 2)
        return round(number, 2)

    return number


def format_date_value(value: Any) -> str | None:
    parsed_date = parse_date_value(value)
    if parsed_date is not None:
        return parsed_date.isoformat()

    if value is None:
        return None

    if isinstance(value, str):
        candidate = value.strip()
        return candidate or None

    return str(value)


def format_timestamp_value(value: Any, fallback: datetime) -> str:
    if value is None:
        return fallback.isoformat(timespec="seconds")

    parsed_datetime = parse_datetime_value(value)
    if parsed_datetime is not None:
        return parsed_datetime.isoformat(timespec="seconds")

    parsed_date = parse_date_value(value)
    if parsed_date is not None:
        return datetime.combine(parsed_date, datetime.min.time()).isoformat(timespec="seconds")

    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            return candidate

    return fallback.isoformat(timespec="seconds")


def compute_revpar(occupancy_pct: Any, adr: Any):
    occupancy_value = parse_number(occupancy_pct)
    adr_value = parse_number(adr)

    if isinstance(occupancy_value, (int, float)) and isinstance(adr_value, (int, float)):
        return round((occupancy_value * adr_value) / 100, 2)

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

        aliases = metadata.get("aliases", [])
        normalized_aliases = []

        if isinstance(aliases, list):
            normalized_aliases = [
                canonicalize_text(alias)
                for alias in aliases
                if isinstance(alias, str) and alias.strip()
            ]

        normalized_name = canonicalize_text(canonical_name)

        registry.append(
            {
                "canonical_name": canonical_name.strip(),
                "normalized_name": normalized_name,
                "tokens": tuple(normalized_name.split()),
                "aliases": normalized_aliases,
            }
        )

    registry.sort(key=lambda item: len(item["tokens"]), reverse=True)

    if not registry:
        raise ValueError(f"No valid hotel names found in {HOTELS_PATH}")

    return registry


def normalize_hotel_name(raw_hotel_name: Any) -> str | None:
    if raw_hotel_name is None:
        return None

    candidate = str(raw_hotel_name).strip()
    if not candidate:
        return None

    normalized_candidate = canonicalize_text(candidate)
    candidate_tokens = set(normalized_candidate.split())

    for hotel in load_hotel_registry():
        canonical_name = hotel["canonical_name"]
        canonical_normalized = hotel["normalized_name"]
        canonical_tokens = set(hotel["tokens"])

        if normalized_candidate == canonical_normalized:
            return canonical_name

        if normalized_candidate in canonical_normalized or canonical_normalized in normalized_candidate:
            return canonical_name

        if normalized_candidate in hotel["aliases"]:
            return canonical_name

        if canonical_tokens.issubset(candidate_tokens):
            return canonical_name

    return candidate


def clear_and_write_tab(worksheet, rows: list[list[Any]]) -> None:
    worksheet.clear()
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")


def build_actual_candidate(record: dict[str, Any], run_timestamp: datetime):
    hotel_name = normalize_hotel_name(record.get("hotel_name"))
    date_value = parse_date_value(record.get("business_date"))

    if not hotel_name or date_value is None:
        return None

    candidate = {
        "hotel_name": hotel_name,
        "date": date_value.isoformat(),
        "month_number": date_value.month,
        "month_name": MONTHS_BY_NUMBER.get(date_value.month),
        "data_type": "Actual",
        "rooms_sold": parse_number(record.get("rooms_sold")),
        "occupancy_pct": normalize_percentage(record.get("occupancy_pct")),
        "adr": parse_number(record.get("adr")),
        "revpar": parse_number(record.get("revpar")),
        "room_revenue": parse_number(record.get("room_revenue")),
        "total_revenue": parse_number(
            record.get("gross_revenue")
            if record.get("gross_revenue") is not None
            else record.get("total_revenue")
        ),
        "source_file_name": record.get("source_file_name"),
        "forecast_snapshot_date": None,
        "import_time": run_timestamp.isoformat(timespec="seconds"),
    }

    import_marker = parse_datetime_value(record.get("import_time")) or datetime.min
    marker = (import_marker, import_marker)
    return candidate, marker


def build_forecast_candidate(record: dict[str, Any], run_timestamp: datetime):
    hotel_name = normalize_hotel_name(record.get("hotel_name"))
    date_value = parse_date_value(record.get("stay_date"))

    if not hotel_name or date_value is None:
        return None

    snapshot_source = record.get("snapshot_date")
    snapshot_marker = parse_datetime_value(snapshot_source)
    import_marker = parse_datetime_value(record.get("import_time")) or datetime.min
    primary_marker = snapshot_marker or import_marker
    marker = (primary_marker, import_marker)

    occupancy_pct = normalize_percentage(record.get("occupancy_pct"))
    adr = parse_number(record.get("avg_room_revenue"))

    candidate = {
        "hotel_name": hotel_name,
        "date": date_value.isoformat(),
        "month_number": date_value.month,
        "month_name": MONTHS_BY_NUMBER.get(date_value.month),
        "data_type": "Forecast",
        "rooms_sold": parse_number(record.get("sold")),
        "occupancy_pct": occupancy_pct,
        "adr": adr,
        "revpar": compute_revpar(occupancy_pct, adr),
        "room_revenue": parse_number(record.get("room_revenue")),
        "total_revenue": None,
        "source_file_name": record.get("source_file_name"),
        "forecast_snapshot_date": format_timestamp_value(
            snapshot_source if snapshot_source is not None else record.get("import_time"),
            fallback=run_timestamp,
        ),
        "import_time": run_timestamp.isoformat(timespec="seconds"),
    }

    return candidate, marker


def choose_latest_rows(records: list[dict[str, Any]], builder) -> dict[tuple[str, str], dict[str, Any]]:
    latest_rows: dict[tuple[str, str], tuple[tuple[datetime, datetime], dict[str, Any]]] = {}

    for record in records:
        candidate = builder(record)
        if candidate is None:
            continue

        row, marker = candidate
        row_key = (row["hotel_name"], row["date"])

        existing = latest_rows.get(row_key)
        if existing is None or marker > existing[0]:
            latest_rows[row_key] = (marker, row)

    return {key: value[1] for key, value in latest_rows.items()}


def load_records(sheet_name: str) -> list[dict[str, Any]]:
    workbook = get_google_sheet()
    worksheet = workbook.worksheet(sheet_name)
    return worksheet.get_all_records()


def build_dashboard_rows() -> tuple[list[dict[str, Any]], int, int]:
    run_timestamp = datetime.now()

    daily_records = load_records(SOURCE_DAILY_TAB)
    forecast_records = load_records(SOURCE_FORECAST_TAB)

    actual_rows = choose_latest_rows(daily_records, lambda record: build_actual_candidate(record, run_timestamp))
    forecast_rows = choose_latest_rows(
        forecast_records,
        lambda record: build_forecast_candidate(record, run_timestamp),
    )

    dashboard_rows: dict[tuple[str, str], dict[str, Any]] = dict(forecast_rows)
    dashboard_rows.update(actual_rows)

    ordered_rows = sorted(
        dashboard_rows.values(),
        key=lambda row: (row["hotel_name"] or "", row["date"] or ""),
    )

    actual_written = sum(1 for row in ordered_rows if row.get("data_type") == "Actual")
    forecast_written = sum(1 for row in ordered_rows if row.get("data_type") == "Forecast")

    return ordered_rows, actual_written, forecast_written


def write_dashboard_rows(rows: list[dict[str, Any]]) -> None:
    workbook = get_google_sheet()
    worksheet = workbook.worksheet(TARGET_TAB)

    output_rows = [TARGET_COLUMNS]

    for row in rows:
        output_rows.append([row.get(column, "") for column in TARGET_COLUMNS])

    clear_and_write_tab(worksheet, output_rows)


def run_dashboard_daily() -> dict[str, int]:
    try:
        rows, actual_count, forecast_count = build_dashboard_rows()
    except Exception as exc:
        print(f"Dashboard daily build failed: {exc}")
        print("actual rows: 0")
        print("forecast rows: 0")
        print("total written: 0")
        return {"actual_rows": 0, "forecast_rows": 0, "total_written": 0}

    try:
        write_dashboard_rows(rows)
        total_written = len(rows)
    except Exception as exc:
        print(f"Dashboard daily write failed: {exc}")
        total_written = 0

    print(f"actual rows: {actual_count}")
    print(f"forecast rows: {forecast_count}")
    print(f"total written: {total_written}")

    return {
        "actual_rows": actual_count,
        "forecast_rows": forecast_count,
        "total_written": total_written,
    }


def main() -> None:
    run_dashboard_daily()


if __name__ == "__main__":
    main()
