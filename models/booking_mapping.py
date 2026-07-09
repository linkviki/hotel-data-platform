from services.date_utils import format_date_only


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


def _resolve_snapshot_date(raw_data: dict) -> str:
    snapshot_date = format_date_only(
        raw_data.get("snapshot_date")
        or raw_data.get("email_received_date")
        or raw_data.get("received_date")
        or raw_data.get("message_date")
        or raw_data.get("report_date")
        or raw_data.get("import_time"),
        fallback=raw_data.get("import_time"),
    )
    return snapshot_date


def map_booking_raw_rows(raw_data: dict) -> list[dict]:
    mapped_rows = []

    for index, raw_row in enumerate(raw_data.get("raw_rows", []), start=1):
        values = raw_row.get("values", [])

        row = {
            "snapshot_date": _resolve_snapshot_date(raw_data),
            "report_date": raw_data.get("report_date"),
            "hotel_name": raw_data.get("hotel_name"),
            "stay_date": raw_row.get("stay_date"),
            "source_file_name": raw_data.get("source_file_name"),
            "import_time": raw_data.get("import_time"),
            "status": "MAPPED",
            "notes": "",
            "raw_row_number": index + 1,
            "raw_row_label": raw_row.get("stay_date"),
            "raw_values": values,
        }

        for index, column_name in enumerate(BOOKING_COLUMNS):
            row[column_name] = values[index] if index < len(values) else None

        mapped_rows.append(row)

    return mapped_rows
