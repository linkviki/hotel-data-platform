import calendar


REQUIRED_FIELDS = [
    "hotel_name",
    "year",
    "month_number",
    "month_name",
    "rooms_sold",
    "occupancy_pct",
    "adr",
    "revpar",
    "room_revenue",
    "total_revenue",
    "source_file_name",
    "import_time",
    "status",
    "notes",
]


def validate_historical_row(data: dict) -> list[str]:
    errors = []

    if not data:
        errors.append("No historical row found")
        return errors

    for field in REQUIRED_FIELDS:
        if data.get(field) is None:
            errors.append(f"Missing required field: {field}")

    hotel_name = data.get("hotel_name")
    year = data.get("year")
    month_number = data.get("month_number")
    month_name = data.get("month_name")

    if not hotel_name:
        errors.append("Missing required field: hotel_name")

    if year is None:
        errors.append("Missing required field: year")

    if month_number is None:
        errors.append("Missing required field: month_number")

    if isinstance(month_number, (int, float)) and not (1 <= int(month_number) <= 12):
        errors.append(f"month_number out of range: {month_number}")

    if isinstance(month_number, int) and 1 <= month_number <= 12:
        expected_month_name = calendar.month_name[month_number]
        if isinstance(month_name, str) and month_name.strip().title() != expected_month_name:
            errors.append(
                f"month_name mismatch for {month_number}: expected {expected_month_name}, got {month_name}"
            )

    occupancy_pct = data.get("occupancy_pct")
    if isinstance(occupancy_pct, (int, float)) and not (0 <= occupancy_pct <= 100):
        errors.append(f"occupancy_pct out of range: {occupancy_pct}")

    for field in ["rooms_sold", "room_revenue", "total_revenue", "adr", "revpar"]:
        value = data.get(field)
        if isinstance(value, (int, float)) and value < 0:
            errors.append(f"{field} cannot be negative: {value}")

    return errors
