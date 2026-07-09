from __future__ import annotations

import argparse
import calendar
from datetime import date, datetime
from typing import Any

from transformers.dashboard_daily import (
    MONTHS_BY_NUMBER,
    normalize_hotel_name,
    parse_date_value,
    parse_number,
)
from writers.google_sheets import get_google_sheet


SOURCE_DASHBOARD_TAB = "Dashboard_Daily_Performance"
SOURCE_BUDGET_TAB = "Budget_Monthly"
SOURCE_HISTORICAL_TAB = "Historical_Monthly"
TARGET_TAB = "Dashboard_Monthly_Performance"

TARGET_COLUMNS = [
    "hotel_name",
    "year",
    "month_number",
    "month_name",
    "actual_room_revenue",
    "forecast_remaining_room_revenue",
    "projected_room_revenue",
    "budget_room_revenue",
    "last_year_room_revenue",
    "actual_total_revenue",
    "budget_total_revenue",
    "last_year_total_revenue",
    "actual_occupancy",
    "budget_occupancy",
    "last_year_occupancy",
    "actual_adr",
    "budget_adr",
    "last_year_adr",
    "actual_revpar",
    "budget_revpar",
    "last_year_revpar",
    "budget_variance",
    "yoy_variance",
    "budget_variance_amount",
    "budget_variance_pct",
    "yoy_variance_amount",
    "yoy_variance_pct",
    "forecast_completion_pct",
    "month_status",
    "import_time",
    "status",
    "notes",
]

STATUS_READY = "READY"
STATUS_MISSING_REFERENCE = "MISSING_REFERENCE"


def load_records(sheet_name: str) -> list[dict[str, Any]]:
    workbook = get_google_sheet()
    worksheet = workbook.worksheet(sheet_name)
    return worksheet.get_all_records()


def parse_int_value(value: Any) -> int | None:
    number = parse_number(value)
    if isinstance(number, (int, float)):
        return int(number)
    return None


def parse_float_value(value: Any) -> float | None:
    number = parse_number(value)
    if isinstance(number, (int, float)):
        return float(number)
    return None


def column_name(index: int) -> str:
    name = ""
    current = index

    while current > 0:
        current, remainder = divmod(current - 1, 26)
        name = chr(65 + remainder) + name

    return name


def target_clear_range() -> str:
    return f"A2:{column_name(len(TARGET_COLUMNS))}"


def normalize_metric_value(value: Any) -> float | int | None:
    if value is None:
        return None

    number = parse_number(value)
    if isinstance(number, (int, float)):
        return number

    return None


def average(values: list[float | int]) -> float | None:
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 2)


def sum_values(values: list[float | int]) -> float | int | None:
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    if not numeric_values:
        return None

    total = sum(numeric_values)
    if all(isinstance(value, int) for value in numeric_values) and float(total).is_integer():
        return int(total)

    return round(float(total), 2)


def compute_projection(actual_room_revenue: Any, forecast_room_revenue: Any):
    actual_value = parse_float_value(actual_room_revenue) or 0
    forecast_value = parse_float_value(forecast_room_revenue) or 0
    projected = actual_value + forecast_value

    if projected == 0 and actual_room_revenue is None and forecast_room_revenue is None:
        return None

    return round(projected, 2)


def compute_variance(projected_room_revenue: Any, comparison_room_revenue: Any):
    projected_value = parse_float_value(projected_room_revenue)
    comparison_value = parse_float_value(comparison_room_revenue)

    if projected_value is None or comparison_value is None:
        return None

    return round(projected_value - comparison_value, 2)


def compute_percentage_change(numerator: Any, denominator: Any):
    numerator_value = parse_float_value(numerator)
    denominator_value = parse_float_value(denominator)

    if numerator_value is None or denominator_value in (None, 0):
        return None

    return round((numerator_value / denominator_value) * 100, 2)


def compute_month_status(year: int, month_number: int, reference_date: date | None = None) -> str:
    current_date = reference_date or date.today()
    current_key = current_date.year * 12 + current_date.month
    row_key = year * 12 + month_number

    if row_key < current_key:
        return "Past"
    if row_key == current_key:
        return "Current"
    return "Future"


def parse_start_month(value: str | None) -> date | None:
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        return None


def add_months(value: date, months: int) -> date:
    total_months = value.year * 12 + (value.month - 1) + months
    year = total_months // 12
    month = total_months % 12 + 1
    return date(year, month, 1)


def row_month_key(row: dict[str, Any]) -> int | None:
    year = parse_int_value(row.get("year"))
    month_number = parse_int_value(row.get("month_number"))

    if year is None or month_number is None:
        return None

    return year * 12 + month_number


def filter_rows_by_start_month(rows: list[dict[str, Any]], start_month: date | None) -> list[dict[str, Any]]:
    if start_month is None:
        return rows

    start_key = start_month.year * 12 + start_month.month
    end_key = add_months(start_month, 2).year * 12 + add_months(start_month, 2).month

    filtered_rows = []

    for row in rows:
        row_key = row_month_key(row)
        if row_key is None:
            continue

        if start_key <= row_key <= end_key:
            filtered_rows.append(row)

    return filtered_rows


def prepare_dashboard_daily_groups(records: list[dict[str, Any]]):
    grouped: dict[tuple[str, int, int], dict[str, Any]] = {}

    for record in records:
        hotel_name = normalize_hotel_name(record.get("hotel_name"))
        date_value = parse_date_value(record.get("date"))
        if not hotel_name or date_value is None:
            continue

        year = date_value.year
        month_number = date_value.month
        key = (hotel_name, year, month_number)

        bucket = grouped.setdefault(
            key,
            {
                "hotel_name": hotel_name,
                "year": year,
                "month_number": month_number,
                "month_name": MONTHS_BY_NUMBER.get(month_number, calendar.month_name[month_number]),
                "actual_room_revenue_values": [],
                "forecast_room_revenue_values": [],
                "actual_total_revenue_values": [],
                "actual_rooms_sold_values": [],
                "actual_occupancy_values": [],
                "actual_adr_values": [],
                "actual_revpar_values": [],
            },
        )

        data_type = str(record.get("data_type") or "").strip().lower()
        room_revenue = normalize_metric_value(record.get("room_revenue"))
        total_revenue = normalize_metric_value(record.get("total_revenue"))
        rooms_sold = normalize_metric_value(record.get("rooms_sold"))
        occupancy_pct = normalize_metric_value(record.get("occupancy_pct"))
        adr = normalize_metric_value(record.get("adr"))
        revpar = normalize_metric_value(record.get("revpar"))

        if data_type == "actual":
            if room_revenue is not None:
                bucket["actual_room_revenue_values"].append(room_revenue)
            if total_revenue is not None:
                bucket["actual_total_revenue_values"].append(total_revenue)
            if rooms_sold is not None:
                bucket["actual_rooms_sold_values"].append(rooms_sold)
            if occupancy_pct is not None:
                bucket["actual_occupancy_values"].append(occupancy_pct)
            if adr is not None:
                bucket["actual_adr_values"].append(adr)
            if revpar is not None:
                bucket["actual_revpar_values"].append(revpar)
        elif data_type == "forecast":
            if room_revenue is not None:
                bucket["forecast_room_revenue_values"].append(room_revenue)

    return grouped


def load_reference_map(sheet_name: str) -> dict[tuple[str, int, int], dict[str, Any]]:
    reference_rows = {}

    for record in load_records(sheet_name):
        hotel_name = normalize_hotel_name(record.get("hotel_name"))
        year = parse_int_value(record.get("year"))
        month_number = parse_int_value(record.get("month_number"))

        if not hotel_name or year is None or month_number is None:
            continue

        reference_rows[(hotel_name, year, month_number)] = record

    return reference_rows


def format_output_value(value: Any):
    if value is None:
        return ""
    return value


def build_dashboard_rows() -> tuple[list[dict[str, Any]], int, int]:
    daily_groups = prepare_dashboard_daily_groups(load_records(SOURCE_DASHBOARD_TAB))
    budget_map = load_reference_map(SOURCE_BUDGET_TAB)
    historical_map = load_reference_map(SOURCE_HISTORICAL_TAB)

    rows: list[dict[str, Any]] = []
    missing_budget_count = 0
    missing_last_year_count = 0

    for (hotel_name, year, month_number), bucket in sorted(daily_groups.items()):
        actual_room_revenue = sum_values(bucket["actual_room_revenue_values"])
        forecast_remaining_room_revenue = sum_values(bucket["forecast_room_revenue_values"])
        projected_room_revenue = compute_projection(actual_room_revenue, forecast_remaining_room_revenue)
        actual_total_revenue = sum_values(bucket["actual_total_revenue_values"])
        actual_rooms_sold = sum_values(bucket["actual_rooms_sold_values"])
        actual_occupancy = average(bucket["actual_occupancy_values"])
        actual_revpar = average(bucket["actual_revpar_values"])

        if actual_room_revenue is not None and actual_rooms_sold not in (None, 0):
            actual_adr = round(float(actual_room_revenue) / float(actual_rooms_sold), 2)
        else:
            actual_adr = average(bucket["actual_adr_values"])

        budget_row = budget_map.get((hotel_name, year, month_number))
        historical_row = historical_map.get((hotel_name, year - 1, month_number))

        budget_exists = budget_row is not None
        last_year_exists = historical_row is not None

        if not budget_exists:
            missing_budget_count += 1
        if not last_year_exists:
            missing_last_year_count += 1

        budget_room_revenue = normalize_metric_value(budget_row.get("room_revenue")) if budget_row else None
        budget_total_revenue = normalize_metric_value(budget_row.get("total_revenue")) if budget_row else None
        budget_occupancy = normalize_metric_value(budget_row.get("occupancy_pct")) if budget_row else None
        budget_adr = normalize_metric_value(budget_row.get("adr")) if budget_row else None
        budget_revpar = normalize_metric_value(budget_row.get("revpar")) if budget_row else None

        last_year_room_revenue = normalize_metric_value(historical_row.get("room_revenue")) if historical_row else None
        last_year_total_revenue = normalize_metric_value(historical_row.get("total_revenue")) if historical_row else None
        last_year_occupancy = normalize_metric_value(historical_row.get("occupancy_pct")) if historical_row else None
        last_year_adr = normalize_metric_value(historical_row.get("adr")) if historical_row else None
        last_year_revpar = normalize_metric_value(historical_row.get("revpar")) if historical_row else None

        budget_variance = compute_variance(projected_room_revenue, budget_room_revenue)
        yoy_variance = compute_variance(projected_room_revenue, last_year_room_revenue)
        budget_variance_amount = budget_variance
        budget_variance_pct = compute_percentage_change(budget_variance_amount, budget_room_revenue)
        yoy_variance_amount = yoy_variance
        yoy_variance_pct = compute_percentage_change(yoy_variance_amount, last_year_room_revenue)
        forecast_completion_pct = compute_percentage_change(actual_room_revenue, projected_room_revenue)
        month_status = compute_month_status(year, month_number)

        missing_notes = []
        if not budget_exists:
            missing_notes.append("budget reference missing")
        if not last_year_exists:
            missing_notes.append("last-year reference missing")

        status = STATUS_READY if (budget_exists or last_year_exists) else STATUS_MISSING_REFERENCE
        notes = "; ".join(missing_notes)

        rows.append(
            {
                "hotel_name": hotel_name,
                "year": year,
                "month_number": month_number,
                "month_name": bucket["month_name"],
                "actual_room_revenue": actual_room_revenue,
                "forecast_remaining_room_revenue": forecast_remaining_room_revenue,
                "projected_room_revenue": projected_room_revenue,
                "budget_room_revenue": budget_room_revenue,
                "last_year_room_revenue": last_year_room_revenue,
                "actual_total_revenue": actual_total_revenue,
                "budget_total_revenue": budget_total_revenue,
                "last_year_total_revenue": last_year_total_revenue,
                "actual_occupancy": actual_occupancy,
                "budget_occupancy": budget_occupancy,
                "last_year_occupancy": last_year_occupancy,
                "actual_adr": actual_adr,
                "budget_adr": budget_adr,
                "last_year_adr": last_year_adr,
                "actual_revpar": actual_revpar,
                "budget_revpar": budget_revpar,
                "last_year_revpar": last_year_revpar,
                "budget_variance": budget_variance,
                "yoy_variance": yoy_variance,
                "budget_variance_amount": budget_variance_amount,
                "budget_variance_pct": budget_variance_pct,
                "yoy_variance_amount": yoy_variance_amount,
                "yoy_variance_pct": yoy_variance_pct,
                "forecast_completion_pct": forecast_completion_pct,
                "month_status": month_status,
                "import_time": datetime.now().isoformat(timespec="seconds"),
                "status": status,
                "notes": notes,
            }
        )

    return rows, missing_budget_count, missing_last_year_count


def prepare_target_sheet(worksheet) -> None:
    worksheet.batch_clear([target_clear_range()])
    worksheet.update(range_name="A1", values=[TARGET_COLUMNS])


def write_dashboard_rows(rows: list[dict[str, Any]]) -> None:
    workbook = get_google_sheet()
    worksheet = workbook.worksheet(TARGET_TAB)
    prepare_target_sheet(worksheet)

    output_rows = [[format_output_value(row.get(column)) for column in TARGET_COLUMNS] for row in rows]
    if output_rows:
        worksheet.append_rows(output_rows, value_input_option="USER_ENTERED")


def summarize_missing_reference_counts(rows: list[dict[str, Any]]) -> tuple[int, int]:
    missing_budget_count = 0
    missing_last_year_count = 0

    for row in rows:
        if row.get("budget_room_revenue") in (None, ""):
            missing_budget_count += 1
        if row.get("last_year_room_revenue") in (None, ""):
            missing_last_year_count += 1

    return missing_budget_count, missing_last_year_count


def format_included_months(rows: list[dict[str, Any]]) -> str:
    included_months = []
    seen_labels = set()

    for row in rows:
        label = f"{row.get('year')}-{int(row.get('month_number')):02d} {row.get('month_name')}"
        if label not in seen_labels:
            seen_labels.add(label)
            included_months.append(label)

    return ", ".join(included_months)


def run_dashboard_monthly(start_month: date | None = None) -> dict[str, int]:
    try:
        rows, _, _ = build_dashboard_rows()
        rows = filter_rows_by_start_month(rows, start_month)
    except Exception as exc:
        print(f"Dashboard monthly build failed: {exc}")
        print("included months: ")
        print("monthly rows written: 0")
        print("rows missing budget: 0")
        print("rows missing last year: 0")
        return {
            "monthly_rows_written": 0,
            "rows_missing_budget": 0,
            "rows_missing_last_year": 0,
        }

    rows_missing_budget, rows_missing_last_year = summarize_missing_reference_counts(rows)

    try:
        write_dashboard_rows(rows)
        monthly_rows_written = len(rows)
    except Exception as exc:
        print(f"Dashboard monthly write failed: {exc}")
        monthly_rows_written = 0

    print(f"included months: {format_included_months(rows)}")
    print(f"monthly rows written: {monthly_rows_written}")
    print(f"rows missing budget: {rows_missing_budget}")
    print(f"rows missing last year: {rows_missing_last_year}")

    return {
        "monthly_rows_written": monthly_rows_written,
        "rows_missing_budget": rows_missing_budget,
        "rows_missing_last_year": rows_missing_last_year,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Dashboard_Monthly_Performance from source tabs.")
    parser.add_argument(
        "--start-month",
        dest="start_month",
        default=None,
        help="Optional YYYY-MM month window start; includes that month plus the next two months.",
    )
    arguments = parser.parse_args()
    run_dashboard_monthly(parse_start_month(arguments.start_month))


if __name__ == "__main__":
    main()
