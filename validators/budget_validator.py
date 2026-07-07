def validate_budget_rows(rows: list[dict]) -> list[str]:
    errors = []

    if not rows:
        errors.append("No budget rows found")
        return errors

    seen_keys = set()

    for index, row in enumerate(rows, start=1):
        hotel_name = row.get("hotel_name")
        year = row.get("year")
        month_number = row.get("month_number")

        key = (hotel_name, year, month_number)

        if key in seen_keys:
            errors.append(f"Row {index}: duplicate row for {key}")

        seen_keys.add(key)

        if not hotel_name:
            errors.append(f"Row {index}: missing hotel_name")

        if year is None:
            errors.append(f"Row {index}: missing year")

        if month_number is None:
            errors.append(f"Row {index}: missing month_number")

        for field in [
            "room_revenue",
            "total_revenue",
            "occupancy_pct",
            "adr",
            "revpar",
        ]:
            if row.get(field) is None:
                errors.append(f"Row {index}: missing {field}")

        if isinstance(month_number, (int, float)) and not (1 <= int(month_number) <= 12):
            errors.append(f"Row {index}: month_number out of range: {month_number}")

        occupancy_pct = row.get("occupancy_pct")
        if isinstance(occupancy_pct, (int, float)) and not (0 <= occupancy_pct <= 100):
            errors.append(f"Row {index}: occupancy_pct out of range: {occupancy_pct}")

        for field in ["room_revenue", "total_revenue", "adr", "revpar"]:
            value = row.get(field)
            if isinstance(value, (int, float)) and value < 0:
                errors.append(f"Row {index}: {field} cannot be negative: {value}")

    return errors
