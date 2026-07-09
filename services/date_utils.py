from __future__ import annotations

from datetime import date, datetime
from typing import Any


def parse_date_value(value: Any) -> date | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None

        normalized_candidate = candidate.replace("Z", "+00:00")
        for pattern in (
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y",
            "%m/%d/%Y %H:%M:%S",
        ):
            try:
                return datetime.strptime(candidate, pattern).date()
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(normalized_candidate).date()
        except ValueError:
            return None

    return None


def format_date_only(value: Any, fallback: Any = None) -> str:
    parsed_date = parse_date_value(value)
    if parsed_date is not None:
        return parsed_date.isoformat()

    fallback_date = parse_date_value(fallback)
    if fallback_date is not None:
        return fallback_date.isoformat()

    if value is None:
        if fallback is None:
            return ""
        return str(fallback).strip()

    candidate_text = str(value).strip()
    if candidate_text:
        return candidate_text

    if fallback is None:
        return ""

    return str(fallback).strip()
