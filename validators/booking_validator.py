def validate_mapped_booking_rows(rows: list[dict]) -> list[str]:
    errors = []

    if not rows:
        errors.append("No mapped booking rows found")
        return errors

    seen_keys = set()

    for index, row in enumerate(rows, start=1):
        hotel_name = row.get("hotel_name")
        snapshot_date = row.get("snapshot_date")
        stay_date = row.get("stay_date")

        key = (hotel_name, snapshot_date, stay_date)

        if key in seen_keys:
            errors.append(f"Row {index}: duplicate row for {key}")

        seen_keys.add(key)

        if not hotel_name:
            errors.append(f"Row {index}: missing hotel_name")

        if not snapshot_date:
            errors.append(f"Row {index}: missing snapshot_date")

        if not stay_date:
            errors.append(f"Row {index}: missing stay_date")

        if row.get("sold") is None:
            errors.append(f"Row {index}: missing sold")

        if row.get("occupancy_pct") is None:
            errors.append(f"Row {index}: missing occupancy_pct")

        if row.get("room_revenue") is None:
            errors.append(f"Row {index}: missing room_revenue")

        if row.get("avg_room_revenue") is None:
            errors.append(f"Row {index}: missing avg_room_revenue")

        sold = row.get("sold")
        occupancy_pct = row.get("occupancy_pct")
        room_revenue = row.get("room_revenue")
        avg_room_revenue = row.get("avg_room_revenue")

        if isinstance(occupancy_pct, (int, float)) and not (0 <= occupancy_pct <= 100):
            errors.append(
                f"Row {index}: occupancy_pct out of range: {occupancy_pct}"
            )

        if isinstance(sold, (int, float)) and sold < 0:
            errors.append(f"Row {index}: sold cannot be negative: {sold}")

        if isinstance(room_revenue, (int, float)) and room_revenue < 0:
            errors.append(f"Row {index}: room_revenue cannot be negative: {room_revenue}")

        if isinstance(avg_room_revenue, (int, float)) and avg_room_revenue < 0:
            errors.append(
                f"Row {index}: avg_room_revenue cannot be negative: {avg_room_revenue}"
            )

    return errors
