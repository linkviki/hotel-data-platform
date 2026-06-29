import os
from dotenv import load_dotenv
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

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