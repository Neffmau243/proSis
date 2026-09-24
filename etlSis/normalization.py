"""Conservative conversions: preserve identifiers; flag damage; never truncate."""
from __future__ import annotations

from datetime import date, datetime
import re
import unicodedata


def normalized_name(value) -> str:
    # Only for catalog lookup. Patient names/identifiers are never merged by this key.
    return " ".join(str(value or "").strip().casefold().split())


def text_problems(value: str) -> list[str]:
    problems = []
    if "\ufffd" in value:
        problems.append("replacement_character")
    if any(unicodedata.category(c) in {"Cs", "Co"} for c in value):
        problems.append("invalid_or_private_unicode")
    if any(unicodedata.category(c) in {"Cc", "Cf"} and c not in "\t\n\r" for c in value):
        problems.append("control_character")
    # A suspicion is a review reason, never an automatic encode/decode repair.
    if re.search(r"(?:Ã[\x80-\xbf]|Â[\x80-\xbf]|â[€\x80-\xbf])", value):
        problems.append("possible_mojibake")
    return problems


def clean_text(value, field: str, issues: list, limit: int | None = None):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        issues.append({"codigo": "unexpected_text_type", "campo": field})
        return None
    result = value.strip()
    if result != value:
        issues.append({"codigo": "trim_outer_whitespace", "campo": field})
    problems = text_problems(result)
    if limit is not None and len(result) > limit:
        problems.append("overlength")
    for problem in problems:
        issues.append({"codigo": problem, "campo": field})
    return None if problems else result or None


def source_date(value, field: str, issues: list, *, as_of: date, required=False):
    if not value:
        if required:
            issues.append({"codigo": "missing_date", "campo": field})
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None or parsed.year < 1900 or parsed.date() > as_of:
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        issues.append({"codigo": "invalid_date", "campo": field})
        return None


def positive_int(value):
    return value if type(value) is int and 0 < value <= 18446744073709551615 else None


def dni(value) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if re.fullmatch(r"[0-9]{8}", value) and len(set(value)) > 1 else None
