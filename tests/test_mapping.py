"""Tests for required-column validation and canonical mapping."""

import pandas as pd
import pytest

from staffing_review.services.mapping import MissingColumnsError, map_to_canonical


def test_maps_common_header_aliases() -> None:
    source = pd.DataFrame(
        {
            "Employee": ["Morgan Reed"],
            "Primary Job": ["CNA"],
            "Work Date": ["2026-08-04"],
            "Shift Start": ["11:00 PM"],
            "Department": ["SNF"],
            "Level": ["Ground"],
            "Ignored": ["value"],
        }
    )

    result = map_to_canonical(source)

    assert result.columns.tolist() == [
        "source_row",
        "employee_name",
        "role",
        "shift_date",
        "start_time",
        "unit",
        "floor",
    ]
    assert result.loc[0, "source_row"] == 2
    assert result.loc[0, "employee_name"] == "Morgan Reed"
    assert result.loc[0, "role"] == "CNA"


def test_reports_all_missing_required_columns() -> None:
    source = pd.DataFrame({"Employee Name": ["Casey Brooks"]})

    with pytest.raises(MissingColumnsError) as error:
        map_to_canonical(source)

    assert error.value.missing == ["floor", "shift_date", "start_time", "unit"]
