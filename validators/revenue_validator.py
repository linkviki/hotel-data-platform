def validate_revenue_report(data: dict) -> list[str]:
    errors = []

    required_fields = [
        "business_date",
        "hotel_name",
        "room_revenue",
        "gross_revenue",
        "rooms_sold",
        "rooms_available",
        "occupancy_pct",
        "adr",
        "revpar",
    ]

    for field in required_fields:
        if data.get(field) is None:
            errors.append(f"Missing required field: {field}")

    if data.get("rooms_sold") and data.get("rooms_available"):
        expected_occ = round((data["rooms_sold"] / data["rooms_available"]) * 100, 2)
        actual_occ = round(data["occupancy_pct"], 2)

        if abs(expected_occ - actual_occ) > 0.1:
            errors.append(
                f"Occupancy mismatch: expected {expected_occ}, got {actual_occ}"
            )

    if data.get("room_revenue") and data.get("rooms_sold"):
        expected_adr = round(data["room_revenue"] / data["rooms_sold"], 2)
        actual_adr = round(data["adr"], 2)

        if abs(expected_adr - actual_adr) > 0.1:
            errors.append(
                f"ADR mismatch: expected {expected_adr}, got {actual_adr}"
            )

    if data.get("room_revenue") and data.get("rooms_available"):
        expected_revpar = round(data["room_revenue"] / data["rooms_available"], 2)
        actual_revpar = round(data["revpar"], 2)

        if abs(expected_revpar - actual_revpar) > 0.1:
            errors.append(
                f"RevPAR mismatch: expected {expected_revpar}, got {actual_revpar}"
            )

    return errors