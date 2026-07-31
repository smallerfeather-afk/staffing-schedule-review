"""Integration tests for the review-service pipeline."""

import pandas as pd

from staffing_review.services.review import prepare_source_records, review_records


def test_prepares_source_rows_and_revalidates_edits() -> None:
    source = pd.DataFrame(
        {
            "Employee Name": ["Late Shift", "Early Shift"],
            "Date": ["2026-08-03", "2026-08-03"],
            "Start Time": ["3:00 PM", "7:00 AM"],
            "Unit": ["SNF", "AL"],
            "Floor": ["3", "1"],
        }
    )

    prepared = prepare_source_records(source)

    assert prepared["employee_name"].tolist() == ["Early Shift", "Late Shift"]
    assert prepared["start_time"].tolist() == ["07:00", "15:00"]
    assert prepared["validation_status"].tolist() == ["Valid", "Valid"]

    prepared.loc[0, "floor"] = ""
    reviewed = review_records(prepared)

    invalid = reviewed.loc[reviewed["employee_name"] == "Early Shift"].iloc[0]
    assert invalid["validation_status"] == "Invalid"
    assert invalid["validation_messages"] == "Floor is required"


def test_excludes_default_location_records_from_all_units() -> None:
    source = pd.DataFrame(
        {
            "Employee Name": [
                "AL Default",
                "MC Default",
                "SNF Default",
                "Floor Staff",
            ],
            "Date": ["2026-08-03"] * 4,
            "Start Time": ["7:00 AM"] * 4,
            "Unit": ["AL", "MC", "SNF", "SNF"],
            "Floor": [
                "Default",
                " WDI- default ",
                "WDI - DEFAULT",
                "S1 James",
            ],
        }
    )

    prepared = prepare_source_records(source)

    assert prepared["employee_name"].tolist() == ["Floor Staff"]
    assert prepared["floor"].tolist() == ["S1 James"]
