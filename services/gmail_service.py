from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import re
import sys
from email.utils import parseaddr
from pathlib import Path

import requests
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

load_dotenv()

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.modify"
SPREADSHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SCOPES = [GMAIL_SCOPE, SPREADSHEETS_SCOPE]

CLIENT_SECRET_FILE = Path(os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials/client_secret.json"))
TOKEN_FILE = Path(os.getenv("GOOGLE_TOKEN_FILE", "credentials/token.json"))
DOWNLOAD_DIR = Path("input/gmail")
DEFAULT_QUERY = "newer_than:7d has:attachment filename:pdf"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
UNDERSCORES = re.compile(r"_+")
MAX_FILENAME_LENGTH = 120
RETRY_DELAYS = (2, 5, 10)


def _save_credentials(creds: Credentials) -> None:
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")


def _load_credentials_from_disk() -> Credentials | None:
    if not TOKEN_FILE.exists():
        return None

    try:
        return Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    except (ValueError, json.JSONDecodeError):
        return None


def _get_credentials() -> Credentials:
    creds = _load_credentials_from_disk()

    if creds and creds.valid and creds.has_scopes(SCOPES):
        return creds

    if creds and creds.expired and creds.refresh_token and creds.has_scopes(SCOPES):
        creds.refresh(Request())
        _save_credentials(creds)
        return creds

    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError(f"Missing Gmail client secret file: {CLIENT_SECRET_FILE}")

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    return creds


def _gmail_request(
    creds: Credentials,
    method: str,
    path: str,
    *,
    params: dict | None = None,
) -> requests.Response:
    url = f"{GMAIL_API_BASE}{path}"
    headers = {"Authorization": f"Bearer {creds.token}"}

    response = requests.request(method, url, headers=headers, params=params, timeout=30)

    if response.status_code == 401 and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)
        headers["Authorization"] = f"Bearer {creds.token}"
        response = requests.request(method, url, headers=headers, params=params, timeout=30)

    response.raise_for_status()
    return response


def _is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, HttpError):
        status = getattr(exc.resp, "status", None)
        return status in {429, 500, 502, 503, 504}

    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        return status in {429, 500, 502, 503, 504}

    if isinstance(exc, requests.RequestException):
        return True

    return False


def _gmail_request_with_retry(
    creds: Credentials,
    method: str,
    path: str,
    *,
    params: dict | None = None,
) -> requests.Response:
    last_error: Exception | None = None

    for attempt, delay in enumerate((0, *RETRY_DELAYS), start=1):
        if attempt > 1:
            time.sleep(delay)

        try:
            return _gmail_request(creds, method, path, params=params)
        except Exception as exc:
            if isinstance(exc, requests.HTTPError):
                status = exc.response.status_code if exc.response is not None else None
                if status == 403:
                    raise
            if isinstance(exc, HttpError) and getattr(exc.resp, "status", None) == 403:
                raise

            if attempt == len(RETRY_DELAYS) + 1 or not _is_retryable_exception(exc):
                raise

            last_error = exc
            print(f"Gmail API attempt {attempt} failed for {path}: {exc}")

    if last_error is not None:
        raise last_error

    raise RuntimeError("Gmail request failed unexpectedly")


def _sanitize_filename(filename: str) -> str:
    safe_name = INVALID_FILENAME_CHARS.sub("_", Path(filename).name)
    safe_name = safe_name.replace(" ", "_")
    safe_name = UNDERSCORES.sub("_", safe_name).strip("._")

    if not safe_name:
        safe_name = "attachment"

    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"

    return safe_name


def _sanitize_slug(value: str, fallback: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("_", value)
    cleaned = cleaned.replace(" ", "_")
    cleaned = UNDERSCORES.sub("_", cleaned).strip("._")
    return cleaned or fallback


def _get_sender_slug(message: dict) -> str:
    headers = message.get("payload", {}).get("headers", []) or []
    from_value = ""

    for header in headers:
        if str(header.get("name", "")).lower() == "from":
            from_value = header.get("value", "") or ""
            break

    display_name, email_address = parseaddr(from_value)
    candidate = display_name or email_address or from_value or "unknown_sender"
    candidate = candidate.split("@", 1)[0] if "@" in candidate and not display_name else candidate
    return _sanitize_slug(candidate, "unknown_sender")


def _build_download_filename(sender_slug: str, message_id: str, filename: str) -> str:
    sanitized_original = _sanitize_filename(filename)
    original_stem = Path(sanitized_original).stem
    extension = ".pdf"
    separator = "__"
    message_id_short = (message_id or "")[:10]
    sender_slug = _sanitize_slug(sender_slug, "unknown_sender")

    if not message_id_short:
        message_id_short = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:10]

    max_total_length = MAX_FILENAME_LENGTH
    minimum_original_length = 1
    max_sender_length = max_total_length - len(separator) * 2 - len(message_id_short) - len(extension) - minimum_original_length
    if max_sender_length < 1:
        max_sender_length = 1

    sender_slug = sender_slug[:max_sender_length].rstrip("._") or "unknown_sender"

    prefix = f"{sender_slug}{separator}{message_id_short}{separator}"
    available_original_length = max_total_length - len(prefix) - len(extension)

    if available_original_length < 1:
        sender_budget = max_total_length - len(separator) * 2 - len(message_id_short) - len(extension) - minimum_original_length
        sender_budget = max(sender_budget, 1)
        sender_slug = sender_slug[:sender_budget].rstrip("._") or "unknown_sender"
        prefix = f"{sender_slug}{separator}{message_id_short}{separator}"
        available_original_length = max_total_length - len(prefix) - len(extension)

    if available_original_length < 1:
        raise ValueError("Unable to build a safe filename within the maximum length limit")

    trimmed_original = original_stem[:available_original_length].rstrip(" ._") or "attachment"
    return f"{prefix}{trimmed_original}{extension}"


def _iter_message_parts(part: dict) -> list[dict]:
    parts = [part]

    for child_part in part.get("parts", []) or []:
        parts.extend(_iter_message_parts(child_part))

    return parts


def _extract_pdf_attachments(message: dict) -> list[dict]:
    attachments: list[dict] = []
    payload = message.get("payload", {})
    message_id = message.get("id", "")

    for part in _iter_message_parts(payload):
        filename = part.get("filename") or ""
        mime_type = str(part.get("mimeType", "")).lower()
        body = part.get("body", {}) or {}
        attachment_id = body.get("attachmentId")
        inline_data = body.get("data")

        if not filename and mime_type != "application/pdf":
            continue

        if not filename.lower().endswith(".pdf") and mime_type != "application/pdf":
            continue

        if not attachment_id and not inline_data:
            continue

        attachments.append(
            {
                "message_id": message_id,
                "attachment_id": attachment_id,
                "filename": filename or "attachment.pdf",
                "inline_data": inline_data,
            }
        )

    return attachments


def _decode_inline_data(data: str) -> bytes:
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def _write_pdf_bytes(
    pdf_bytes: bytes,
    *,
    download_dir: Path,
    message_id: str,
    attachment_id: str | None,
    sender_slug: str,
    filename: str,
) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = _build_download_filename(sender_slug, message_id, filename)
    candidate = download_dir / safe_filename
    counter = 1

    while candidate.exists():
        suffix = f"_{counter}"
        prefixed_name = _build_download_filename(sender_slug, message_id, filename)
        stem = Path(prefixed_name).stem
        extension = Path(prefixed_name).suffix or ".pdf"
        max_stem_length = MAX_FILENAME_LENGTH - len(suffix) - len(extension)

        if max_stem_length < 1:
            raise ValueError("Unable to build a unique safe filename within the maximum length limit")

        candidate = download_dir / f"{stem[:max_stem_length]}{suffix}{extension}"
        counter += 1

    candidate.write_bytes(pdf_bytes)
    return candidate


def _list_matching_messages(creds: Credentials, query: str) -> list[dict]:
    messages: list[dict] = []
    params: dict[str, str | int] = {"q": query, "maxResults": 100}

    while True:
        response = _gmail_request_with_retry(creds, "GET", "/users/me/messages", params=params)
        payload = response.json()

        messages.extend(payload.get("messages", []))

        next_page_token = payload.get("nextPageToken")
        if not next_page_token:
            break

        params["pageToken"] = next_page_token

    return messages


def download_pdf_attachments(
    query: str = DEFAULT_QUERY,
    download_dir: Path = DOWNLOAD_DIR,
) -> list[Path]:
    creds = _get_credentials()
    downloaded_paths: list[Path] = []

    for message_summary in _list_matching_messages(creds, query):
        message_id = message_summary.get("id")
        if not message_id:
            continue

        try:
            message_response = _gmail_request_with_retry(
                creds,
                "GET",
                f"/users/me/messages/{message_id}",
                params={"format": "full"},
            )
            message = message_response.json()
            sender_slug = _get_sender_slug(message)

            for attachment in _extract_pdf_attachments(message):
                try:
                    inline_data = attachment.get("inline_data")
                    attachment_id = attachment.get("attachment_id")

                    if inline_data:
                        pdf_bytes = _decode_inline_data(inline_data)
                    else:
                        attachment_response = _gmail_request_with_retry(
                            creds,
                            "GET",
                            f"/users/me/messages/{message_id}/attachments/{attachment_id}",
                        )
                        pdf_bytes = _decode_inline_data(attachment_response.json()["data"])

                    saved_path = _write_pdf_bytes(
                        pdf_bytes,
                        download_dir=download_dir,
                        message_id=message_id,
                        attachment_id=attachment_id,
                        sender_slug=sender_slug,
                        filename=attachment["filename"],
                    )
                    downloaded_paths.append(saved_path)
                except Exception as exc:
                    print(f"Failed to download attachment from message {message_id[:10]}: {exc}")
        except Exception as exc:
            print(f"Failed to process Gmail message {message_id[:10]}: {exc}")

    return downloaded_paths


def main() -> int:
    try:
        downloaded_paths = download_pdf_attachments()
    except Exception as exc:
        print(f"Failed to download Gmail PDF attachments: {exc}", file=sys.stderr)
        return 1

    if not downloaded_paths:
        print("No PDF attachments downloaded.")
        return 0

    for path in downloaded_paths:
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
