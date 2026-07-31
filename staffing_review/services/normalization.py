"""Normalize editable schedule values while preserving invalid input."""

from datetime import date, datetime, time
from typing import Any

import pandas as pd

from staffing_review.constants import RECORD_FIELDS, UNIT_ALIASES


def is_blank(value: Any) -> bool:
    """Return whether a cell has no meaningful value."""
    if value is None or value is pd.NA:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return not str(value).strip()


def normalize_text(value: Any) -> str:
    if is_blank(value):
        return ""
    return " ".join(str(value).strip().split())


def normalize_date(value: Any) -> str:
    """Normalize a date to ISO text, retaining unparseable source text."""
    if is_blank(value):
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = normalize_text(value)
    try:
        parsed = pd.to_datetime(text, errors="raise")
    except (TypeError, ValueError, OverflowError):
        return text
    return parsed.date().isoformat()


def normalize_time(value: Any) -> str:
    """Normalize a start time to 24-hour HH:MM text."""
    if is_blank(value):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%H:%M")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, (int, float)) and 0 <= float(value) < 1:
        minutes = round(float(value) * 24 * 60) % (24 * 60)
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    text = normalize_text(value)
    try:
        parsed = pd.to_datetime(text, errors="raise")
    except (TypeError, ValueError, OverflowError):
        return text
    return parsed.strftime("%H:%M")


def normalize_floor(value: Any) -> str:
    if is_blank(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return normalize_text(value)


def normalize_records(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize all editable canonical fields in a copied DataFrame."""
    normalized = data.copy()
    for field in RECORD_FIELDS:
        if field not in normalized:
            normalized[field] = ""

    normalized["employee_name"] = normalized["employee_name"].map(normalize_text)
    normalized["role"] = normalized["role"].map(normalize_text)
    normalized["shift_date"] = normalized["shift_date"].map(normalize_date)
    normalized["start_time"] = normalized["start_time"].map(normalize_time)
    normalized["unit"] = normalized["unit"].map(
        lambda value: UNIT_ALIASES.get(
            normalize_text(value).casefold(), normalize_text(value)
        )
    )
    normalized["floor"] = normalized["floor"].map(normalize_floor)
    return normalized
