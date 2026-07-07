import calendar


EXPECTED_MONTH_NUMBERS = set(range(1, 13))
REQUIRED_FIELDS = [
    "hotel_name",
    "year",
    "month_number",
    "month_name",
    "available_rooms",
    "rooms_sold",
    "occupancy_pct",
    "adr",
    "revpar",
    "room_revenue",
    "fb_revenue",
    "misc_revenue",
    "total_revenue",
    "source_file_name",
    "import_time",
    "status",
    "notes",
]


def validate_budget_rows(rows: list[dict]) -> list[str]:
    errors = []

    if not rows:
        errors.append("No budget rows found")
        return errors

    seen_keys = set()
    seen_months = set()

    for index, row in enumerate(rows, start=1):
        hotel_name = row.get("hotel_name")
        year = row.get("year")
        month_number = row.get("month_number")
        month_name = row.get("month_name")

        key = (hotel_name, year, month_number)

        if key in seen_keys:
            errors.append(f"Row {index}: duplicate row for {key}")

        seen_keys.add(key)

        for field in REQUIRED_FIELDS:
            if row.get(field) is None:
                errors.append(f"Row {index}: missing {field}")

        if not hotel_name:
            errors.append(f"Row {index}: missing hotel_name")

        if year is None:
            errors.append(f"Row {index}: missing year")

        if month_number is None:
            errors.append(f"Row {index}: missing month_number")

        if isinstance(month_number, (int, float)) and not (1 <= int(month_number) <= 12):
            errors.append(f"Row {index}: month_number out of range: {month_number}")

        if isinstance(month_number, int) and 1 <= month_number <= 12:
            seen_months.add(month_number)

            expected_month_name = calendar.month_name[month_number]
            if isinstance(month_name, str) and month_name.strip().title() != expected_month_name:
                errors.append(
                    f"Row {index}: month_name mismatch for {month_number}: "
                    f"expected {expected_month_name}, got {month_name}"
                )

        occupancy_pct = row.get("occupancy_pct")
        if isinstance(occupancy_pct, (int, float)) and not (0 <= occupancy_pct <= 100):
            errors.append(f"Row {index}: occupancy_pct out of range: {occupancy_pct}")

        for field in ["available_rooms", "rooms_sold", "room_revenue", "fb_revenue", "misc_revenue", "total_revenue", "adr", "revpar"]:
            value = row.get(field)
            if isinstance(value, (int, float)) and value < 0:
                errors.append(f"Row {index}: {field} cannot be negative: {value}")

    missing_months = EXPECTED_MONTH_NUMBERS - seen_months
    if missing_months:
        missing_month_names = [calendar.month_name[number] for number in sorted(missing_months)]
        errors.append(f"Missing budget months: {', '.join(missing_month_names)}")

    return errors
