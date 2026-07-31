"""Tests for CSV and Excel schedule readers."""

from io import BytesIO

import pandas as pd
import pytest

from staffing_review.io.readers import ScheduleReadError, read_schedule


def test_reads_utf8_csv() -> None:
    payload = BytesIO(b"employee_name,shift_date\nAvery Stone,2026-08-03\n")

    result = read_schedule(payload, filename="schedule.csv")

    assert result.to_dict("records") == [
        {"employee_name": "Avery Stone", "shift_date": "2026-08-03"}
    ]


def test_reads_xlsx() -> None:
    payload = BytesIO()
    source = pd.DataFrame({"employee_name": ["Jordan Lee"]})
    with pd.ExcelWriter(payload, engine="openpyxl") as writer:
        source.to_excel(writer, index=False)
    payload.seek(0)

    result = read_schedule(payload, filename="schedule.xlsx")

    pd.testing.assert_frame_equal(result, source)


def test_rejects_unsupported_file_type() -> None:
    with pytest.raises(ScheduleReadError, match="Unsupported file type"):
        read_schedule(BytesIO(b"not a schedule"), filename="schedule.pdf")
