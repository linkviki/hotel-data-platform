import os
from dotenv import load_dotenv
import gspread
from gspread import Cell
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from services.date_utils import format_date_only

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials/client_secret.json")
TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "credentials/token.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")


def get_google_sheet():
    if not GOOGLE_SHEET_ID:
        raise ValueError("Missing GOOGLE_SHEET_ID in .env")

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    client = gspread.authorize(creds)
    return client.open_by_key(GOOGLE_SHEET_ID)


def append_daily_hotel_metrics(data: dict):
    sheet = get_google_sheet()
    worksheet = sheet.worksheet("Daily_Hotel_Metrics")

    columns = worksheet.row_values(1)
    records = worksheet.get_all_records()

    key_fields = ["business_date", "hotel_name", "report_type"]

    for record in records:
        if all(str(record.get(field, "")).strip() == str(data.get(field, "")).strip() for field in key_fields):
            print(
                f"Duplicate found. Skipping append for "
                f"{data.get('hotel_name')} | {data.get('business_date')} | {data.get('report_type')}"
            )
            return False

    row = [data.get(column, "") for column in columns]
    worksheet.append_row(row, value_input_option="USER_ENTERED")

    return True


def append_import_log(data: dict, action: str):
    sheet = get_google_sheet()
    worksheet = sheet.worksheet("Import_Log")

    log_row = {
        "import_time": data.get("import_time", ""),
        "hotel_name": data.get("hotel_name", ""),
        "report_type": data.get("report_type", ""),
        "business_date": data.get("business_date", ""),
        "source_file_name": data.get("source_file_name", ""),
        "status": data.get("status", ""),
        "action": action,
        "notes": data.get("notes", ""),
    }

    columns = worksheet.row_values(1)
    row = [log_row.get(column, "") for column in columns]

    worksheet.append_row(row, value_input_option="USER_ENTERED")
    return True


def _ensure_booking_forecast_columns(worksheet):
    columns = worksheet.row_values(1)

    if "snapshot_date" not in columns:
        next_column_index = len(columns) + 1
        worksheet.update_cell(1, next_column_index, "snapshot_date")
        columns.append("snapshot_date")

    return columns


def _normalize_booking_snapshot_date(record: dict) -> str:
    return format_date_only(
        record.get("snapshot_date")
        or record.get("report_date")
        or record.get("import_time"),
        fallback=record.get("import_time"),
    )


def _booking_forecast_key(record: dict) -> tuple[str, str, str]:
    return (
        str(record.get("hotel_name", "")).strip(),
        _normalize_booking_snapshot_date(record),
        str(record.get("stay_date", "")).strip(),
    )


def _normalize_existing_booking_forecast_snapshot_dates(worksheet, columns: list[str]) -> int:
    if "snapshot_date" not in columns:
        return 0

    snapshot_column_index = columns.index("snapshot_date") + 1
    records = worksheet.get_all_records()
    cells_to_update = []

    for row_number, record in enumerate(records, start=2):
        normalized_snapshot_date = _normalize_booking_snapshot_date(record)
        current_snapshot_date = format_date_only(record.get("snapshot_date"))

        if current_snapshot_date != normalized_snapshot_date:
            cells_to_update.append(
                Cell(row_number, snapshot_column_index, normalized_snapshot_date)
            )

    if cells_to_update:
        worksheet.update_cells(cells_to_update, value_input_option="USER_ENTERED")

    return len(cells_to_update)


def append_booking_forecast_rows(rows: list[dict]):
    sheet = get_google_sheet()
    worksheet = sheet.worksheet("Booking_Forecast")

    columns = _ensure_booking_forecast_columns(worksheet)
    normalized_existing_count = _normalize_existing_booking_forecast_snapshot_dates(worksheet, columns)
    records = worksheet.get_all_records()

    existing_keys = {_booking_forecast_key(record) for record in records}
    print(f"Booking_Forecast existing duplicate-key count loaded: {len(existing_keys)}")
    print(f"Booking_Forecast existing rows normalized: {normalized_existing_count}")

    appended_count = 0
    skipped_count = 0
    rows_to_append = []

    for data in rows:
        snapshot_date = _normalize_booking_snapshot_date(data)
        key = (
            str(data.get("hotel_name", "")).strip(),
            snapshot_date,
            str(data.get("stay_date", "")).strip(),
        )

        data["snapshot_date"] = snapshot_date

        if key in existing_keys:
            skipped_count += 1
            continue

        row = [data.get(column, "") for column in columns]
        rows_to_append.append(row)
        existing_keys.add(key)
        appended_count += 1

    if rows_to_append:
        worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

    print(f"Booking_Forecast rows appended: {appended_count}")
    print(f"Booking_Forecast rows skipped: {skipped_count}")

    return {
        "appended": appended_count,
        "skipped": skipped_count,
    }


def append_budget_monthly(rows: list[dict]):
    sheet = get_google_sheet()
    worksheet = sheet.worksheet("Budget_Monthly")

    columns = worksheet.row_values(1)
    records = worksheet.get_all_records()

    existing_keys = {
        (
            str(record.get("hotel_name", "")).strip(),
            str(record.get("year", "")).strip(),
            str(record.get("month_number", "")).strip(),
        )
        for record in records
    }

    appended_count = 0
    skipped_count = 0
    rows_to_append = []

    for data in rows:
        key = (
            str(data.get("hotel_name", "")).strip(),
            str(data.get("year", "")).strip(),
            str(data.get("month_number", "")).strip(),
        )

        if key in existing_keys:
            skipped_count += 1
            continue

        row = [data.get(column, "") for column in columns]
        rows_to_append.append(row)
        existing_keys.add(key)
        appended_count += 1

    if rows_to_append:
        worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

    return {
        "appended": appended_count,
        "skipped": skipped_count,
    }


def append_historical_monthly(rows: list[dict]):
    sheet = get_google_sheet()
    worksheet = sheet.worksheet("Historical_Monthly")

    columns = worksheet.row_values(1)
    records = worksheet.get_all_records()

    existing_keys = {
        (
            str(record.get("hotel_name", "")).strip(),
            str(record.get("year", "")).strip(),
            str(record.get("month_number", "")).strip(),
        )
        for record in records
    }

    appended_count = 0
    skipped_count = 0
    rows_to_append = []

    for data in rows:
        key = (
            str(data.get("hotel_name", "")).strip(),
            str(data.get("year", "")).strip(),
            str(data.get("month_number", "")).strip(),
        )

        if key in existing_keys:
            skipped_count += 1
            continue

        row = [data.get(column, "") for column in columns]
        rows_to_append.append(row)
        existing_keys.add(key)
        appended_count += 1

    if rows_to_append:
        worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")

    return {
        "appended": appended_count,
        "skipped": skipped_count,
    }
