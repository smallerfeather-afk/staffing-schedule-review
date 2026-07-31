"""Tests for stable chronological schedule sorting."""

import pandas as pd

from staffing_review.services.sorting import sort_records


def test_sorts_chronologically_and_places_invalid_values_last() -> None:
    source = pd.DataFrame(
        {
            "employee_name": ["Invalid Row", "Late Shift", "Early Shift"],
            "shift_date": ["bad-date", "2026-08-03", "2026-08-03"],
            "start_time": ["bad-time", "15:00", "07:00"],
        }
    )

    result = sort_records(source)

    assert result["employee_name"].tolist() == [
        "Early Shift",
        "Late Shift",
        "Invalid Row",
    ]
