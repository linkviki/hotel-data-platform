from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


HOTELS_PATH = Path("config/hotels.json")


def canonicalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


@lru_cache(maxsize=1)
def load_hotel_registry() -> list[dict[str, Any]]:
    payload = json.loads(HOTELS_PATH.read_text(encoding="utf-8-sig"))

    if not isinstance(payload, dict):
        raise ValueError(f"Invalid hotel registry structure in {HOTELS_PATH}")

    registry: list[dict[str, Any]] = []

    for canonical_name, metadata in payload.items():
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            continue

        if not isinstance(metadata, dict):
            continue

        aliases = metadata.get("aliases", [])
        normalized_aliases: list[str] = []

        if isinstance(aliases, list):
            normalized_aliases = [
                canonicalize_text(alias)
                for alias in aliases
                if isinstance(alias, str) and alias.strip()
            ]

        normalized_name = canonicalize_text(canonical_name)

        registry.append(
            {
                "canonical_name": canonical_name.strip(),
                "normalized_name": normalized_name,
                "tokens": tuple(normalized_name.split()),
                "aliases": normalized_aliases,
            }
        )

    registry.sort(key=lambda item: len(item["tokens"]), reverse=True)

    if not registry:
        raise ValueError(f"No valid hotel names found in {HOTELS_PATH}")

    return registry


def _coerce_candidate_text(candidate: Any) -> str | None:
    if candidate is None:
        return None

    candidate_text = str(candidate).strip()
    return candidate_text or None


def _match_hotel(candidate_text: str) -> str | None:
    normalized_candidate = canonicalize_text(candidate_text)
    candidate_tokens = set(normalized_candidate.split())

    for hotel in load_hotel_registry():
        canonical_name = hotel["canonical_name"]
        canonical_normalized = hotel["normalized_name"]
        canonical_tokens = set(hotel["tokens"])

        if normalized_candidate == canonical_normalized:
            return canonical_name

        if normalized_candidate in canonical_normalized or canonical_normalized in normalized_candidate:
            return canonical_name

        if normalized_candidate in hotel["aliases"]:
            return canonical_name

        if canonical_tokens.issubset(candidate_tokens):
            return canonical_name

    return None


def resolve_hotel_name(
    primary_candidate: Any,
    fallback_candidates: Iterable[Any] = (),
) -> dict[str, Any]:
    candidate_sources = [("primary", primary_candidate), *[(f"fallback_{index}", candidate) for index, candidate in enumerate(fallback_candidates, start=1)]]

    raw_candidate = _coerce_candidate_text(primary_candidate)

    for source_name, candidate in candidate_sources:
        candidate_text = _coerce_candidate_text(candidate)
        if candidate_text is None:
            continue

        normalized_name = _match_hotel(candidate_text)
        if normalized_name:
            return {
                "raw_hotel_name": raw_candidate,
                "normalized_hotel_name": normalized_name,
                "resolved_from": source_name,
                "resolved_candidate": candidate_text,
            }

    return {
        "raw_hotel_name": raw_candidate,
        "normalized_hotel_name": None,
        "resolved_from": None,
        "resolved_candidate": None,
    }
