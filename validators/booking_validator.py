def validate_booking_stats(data: dict) -> list[str]:
    errors = []

    if not data.get("hotel_name"):
        errors.append("Missing hotel_name")

    if not data.get("report_type"):
        errors.append("Missing report_type")

    rows = data.get("rows")

    if not isinstance(rows, list) or len(rows) == 0:
        errors.append("Missing booking rows")
        return errors

    for index, row in enumerate(rows, start=1):
        if not row.get("date"):
            errors.append(f"Row {index}: missing date")

        if row.get("rooms_sold") is None:
            errors.append(f"Row {index}: missing rooms_sold")

        if row.get("occupancy_pct") is None:
            errors.append(f"Row {index}: missing occupancy_pct")

    return errors