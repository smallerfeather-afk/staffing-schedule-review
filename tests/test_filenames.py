"""Tests for approved two-week output filenames."""

import pandas as pd
import pytest

from staffing_review.io.filenames import OutlookFilenameError, outlook_filename


def test_uses_first_valid_date_and_full_fourteen_day_span() -> None:
    records = pd.DataFrame(
        {
            "shift_date": ["2026-07-30", "2026-07-31", "2026-08-02"],
            "validation_status": ["Invalid", "Valid", "Valid"],
        }
    )

    assert outlook_filename(records, "AL/MC", "pdf") == (
        "2 Week Outlook - AL-MC - 07.31 to 08.13.pdf"
    )
    assert outlook_filename(records, "SNF", ".xlsx") == (
        "2 Week Outlook - SNF - 07.31 to 08.13.xlsx"
    )


def test_rejects_schedule_without_a_valid_date() -> None:
    records = pd.DataFrame(
        {
            "shift_date": ["not-a-date"],
            "validation_status": ["Invalid"],
        }
    )

    with pytest.raises(OutlookFilenameError, match="valid shift date"):
        outlook_filename(records, "SNF", "pdf")
