BOOKING_COLUMNS = [
    "gtd",
    "non",
    "total",
    "overs",
    "deps",
    "guests",
    "sold",
    "occupancy_pct",
    "room_revenue",
    "avg_room_revenue",
    "group_rooms_not_sold",
    "groups_total",
    "groups_available",
    "groups_occupancy_pct",
]


def map_booking_raw_rows(raw_data: dict) -> list[dict]:
    mapped_rows = []

    for raw_row in raw_data.get("raw_rows", []):
        values = raw_row.get("values", [])

        row = {
            "report_date": raw_data.get("report_date"),
            "hotel_name": raw_data.get("hotel_name"),
            "stay_date": raw_row.get("stay_date"),
            "source_file_name": raw_data.get("source_file_name"),
            "import_time": raw_data.get("import_time"),
            "status": "MAPPED",
            "notes": "",
        }

        for index, column_name in enumerate(BOOKING_COLUMNS):
            row[column_name] = values[index] if index < len(values) else None

        mapped_rows.append(row)

    return mapped_rows