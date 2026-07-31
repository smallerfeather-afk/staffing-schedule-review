"""Tests for row-level review validation."""

import pandas as pd

from staffing_review.services.validation import (
    summarize_validation,
    validate_records,
)


def test_flags_missing_and_invalid_values() -> None:
    source = pd.DataFrame(
        [
            {
                "source_row": 2,
                "employee_name": "",
                "shift_date": "08/40/2026",
                "start_time": "25:00",
                "unit": "Unknown Wing",
                "floor": "#2",
            },
            {
                "source_row": 3,
                "employee_name": "Taylor Quinn",
                "shift_date": "2026-08-05",
                "start_time": "07:00",
                "unit": "Skilled Nursing",
                "floor": "3",
            },
        ]
    )

    result = validate_records(source)
    summary = summarize_validation(result)

    assert result.loc[0, "validation_status"] == "Invalid"
    assert "Employee Name is required" in result.loc[0, "validation_messages"]
    assert "Shift date is invalid" in result.loc[0, "validation_messages"]
    assert "Start time is invalid" in result.loc[0, "validation_messages"]
    assert "Unit must be" in result.loc[0, "validation_messages"]
    assert "Floor contains unsupported characters" in result.loc[
        0, "validation_messages"
    ]
    assert result.loc[1, "validation_status"] == "Valid"
    assert summary.total == 2
    assert summary.valid == 1
    assert summary.invalid == 1
