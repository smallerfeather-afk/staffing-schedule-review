"""Tests for editable value normalization."""

from datetime import date, time

import pandas as pd

from staffing_review.services.normalization import normalize_records


def test_normalizes_dates_times_units_and_text() -> None:
    source = pd.DataFrame(
        {
            "source_row": [2, 3],
            "employee_name": ["  Avery   Stone ", "Riley Chen"],
            "role": ["  Med   Tech ", "CNA"],
            "shift_date": [date(2026, 8, 3), "not-a-date"],
            "start_time": [time(7, 5), 0.5],
            "unit": [" al ", "MC"],
            "floor": [1.0, " 2A "],
        }
    )

    result = normalize_records(source)

    assert result.loc[0].to_dict() == {
        "source_row": 2,
        "employee_name": "Avery Stone",
        "role": "Med Tech",
        "shift_date": "2026-08-03",
        "start_time": "07:05",
        "unit": "Assisted Living",
        "floor": "1",
    }
    assert result.loc[1, "shift_date"] == "not-a-date"
    assert result.loc[1, "start_time"] == "12:00"
    assert result.loc[1, "unit"] == "Memory Care"
    assert result.loc[1, "floor"] == "2A"
