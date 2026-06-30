from pathlib import Path


def detect_report_type(file_path: Path) -> str:
    file_name = file_path.name.lower()

    if "revenue report" in file_name:
        return "REVENUE_REPORT"

    if "booking stats" in file_name:
        return "BOOKING_STATS_REPORT"

    return "UNKNOWN"