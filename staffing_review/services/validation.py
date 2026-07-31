"""Validate normalized schedule records."""

from datetime import datetime
import re

import pandas as pd

from staffing_review.constants import CANONICAL_FIELDS, VALID_UNITS
from staffing_review.schemas import ValidationSummary
from staffing_review.services.normalization import is_blank

FLOOR_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .&/-]{0,39}$")


def _valid_date(value: object) -> bool:
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
    except (TypeError, ValueError):
        return False
    return True


def _valid_time(value: object) -> bool:
    try:
        datetime.strptime(str(value), "%H:%M")
    except (TypeError, ValueError):
        return False
    return True


def validate_records(data: pd.DataFrame) -> pd.DataFrame:
    """Add deterministic row-level validation status and messages."""
    validated = data.copy()
    statuses: list[str] = []
    messages: list[str] = []

    for _, row in validated.iterrows():
        row_messages: list[str] = []

        for field in CANONICAL_FIELDS:
            if is_blank(row.get(field)):
                row_messages.append(f"{field.replace('_', ' ').title()} is required")

        if not is_blank(row.get("shift_date")) and not _valid_date(
            row.get("shift_date")
        ):
            row_messages.append("Shift date is invalid")

        if not is_blank(row.get("start_time")) and not _valid_time(
            row.get("start_time")
        ):
            row_messages.append("Start time is invalid")

        if not is_blank(row.get("unit")) and row.get("unit") not in VALID_UNITS:
            row_messages.append(
                "Unit must be Assisted Living, Memory Care, or Skilled Nursing"
            )

        floor = row.get("floor")
        if not is_blank(floor) and not FLOOR_PATTERN.fullmatch(str(floor)):
            row_messages.append("Floor contains unsupported characters")

        statuses.append("Invalid" if row_messages else "Valid")
        messages.append("; ".join(row_messages))

    validated["validation_status"] = statuses
    validated["validation_messages"] = messages
    return validated


def summarize_validation(data: pd.DataFrame) -> ValidationSummary:
    """Count valid and invalid rows in validated review data."""
    total = len(data)
    invalid = int((data.get("validation_status") == "Invalid").sum())
    return ValidationSummary(total=total, valid=total - invalid, invalid=invalid)
