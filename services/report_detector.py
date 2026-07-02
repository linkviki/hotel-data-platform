from __future__ import annotations

import json
import sys
import re
from pathlib import Path

REPORT_RULES_PATH = Path(__file__).resolve().parents[1] / "config" / "report_rules.json"
_REPORT_RULES_CACHE: list[dict] | None = None
_REPORT_RULES_LOADED = False


def _report_rules_error(message: str) -> None:
    print(message, file=sys.stderr)


def load_report_rules() -> list[dict]:
    global _REPORT_RULES_CACHE, _REPORT_RULES_LOADED

    if _REPORT_RULES_LOADED:
        return _REPORT_RULES_CACHE or []

    _REPORT_RULES_LOADED = True

    try:
        with REPORT_RULES_PATH.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)
    except FileNotFoundError:
        _REPORT_RULES_CACHE = []
        _report_rules_error(f"Report rules file not found: {REPORT_RULES_PATH}")
        return _REPORT_RULES_CACHE
    except json.JSONDecodeError as exc:
        _REPORT_RULES_CACHE = []
        _report_rules_error(f"Invalid report rules JSON in {REPORT_RULES_PATH}: {exc}")
        return _REPORT_RULES_CACHE

    rules = payload.get("rules")
    if not isinstance(rules, list):
        _REPORT_RULES_CACHE = []
        _report_rules_error(
            f"Invalid report rules structure in {REPORT_RULES_PATH}: 'rules' must be a list"
        )
        return _REPORT_RULES_CACHE

    validated_rules: list[dict] = []

    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            _report_rules_error(
                f"Invalid report rule #{index} in {REPORT_RULES_PATH}: expected an object"
            )
            continue

        report_type = rule.get("report_type")
        keywords = rule.get("keywords")

        if not isinstance(report_type, str) or not report_type.strip():
            _report_rules_error(
                f"Invalid report rule #{index} in {REPORT_RULES_PATH}: 'report_type' must be a non-empty string"
            )
            continue

        if not isinstance(keywords, list) or not keywords:
            _report_rules_error(
                f"Invalid report rule #{index} in {REPORT_RULES_PATH}: 'keywords' must be a non-empty list"
            )
            continue

        normalized_keywords = []
        invalid_keyword = False
        for keyword in keywords:
            if not isinstance(keyword, str) or not keyword.strip():
                _report_rules_error(
                    f"Invalid report rule #{index} in {REPORT_RULES_PATH}: keywords must be non-empty strings"
                )
                invalid_keyword = True
                break
            normalized_keywords.append(keyword.strip().lower())

        if invalid_keyword:
            continue

        validated_rules.append(
            {
                "report_type": report_type.strip(),
                "keywords": normalized_keywords,
            }
        )

    if not validated_rules:
        _report_rules_error(f"No valid report rules loaded from {REPORT_RULES_PATH}")

    _REPORT_RULES_CACHE = validated_rules
    return validated_rules


def detect_report_type(file_path: Path) -> str:
    file_name = re.sub(r"[_-]+", " ", file_path.name.lower())
    file_name = re.sub(r"\s+", " ", file_name).strip()

    for rule in load_report_rules():
        for keyword in rule["keywords"]:
            if keyword in file_name:
                return rule["report_type"]

    return "UNKNOWN"
