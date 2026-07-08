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
        room_revenue = row.get("room_revenue")
        fb_revenue = row.get("fb_revenue")
        misc_revenue = row.get("misc_revenue")
        total_revenue = row.get("total_revenue")

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

        coerced_month_number = None
        if isinstance(month_number, int) and 1 <= month_number <= 12:
            coerced_month_number = month_number
        elif isinstance(month_number, float) and month_number.is_integer() and 1 <= int(month_number) <= 12:
            coerced_month_number = int(month_number)
        elif isinstance(month_number, str) and month_number.strip().isdigit():
            maybe_month = int(month_number.strip())
            if 1 <= maybe_month <= 12:
                coerced_month_number = maybe_month

        if coerced_month_number is not None:
            seen_months.add(coerced_month_number)

            expected_month_name = calendar.month_name[coerced_month_number]
            if not isinstance(month_name, str) or month_name.strip().title() != expected_month_name:
                errors.append(
                    f"Row {index}: month_number/month_name mismatch for {coerced_month_number}: "
                    f"expected {expected_month_name}, got {month_name}"
                )

        if all(isinstance(value, (int, float)) for value in [room_revenue, fb_revenue, misc_revenue, total_revenue]):
            expected_total = round(float(room_revenue) + float(fb_revenue) + float(misc_revenue), 2)
            actual_total = round(float(total_revenue), 2)
            if abs(expected_total - actual_total) > 2:
                errors.append(
                    f"Row {index}: total_revenue mismatch: expected approximately {expected_total}, got {actual_total}"
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
