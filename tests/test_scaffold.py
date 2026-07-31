"""Smoke tests for the application scaffold."""

from staffing_review import __version__
from staffing_review.config import APP_TITLE, MILESTONE_LABEL
from staffing_review.constants import CANONICAL_FIELDS


def test_scaffold_metadata() -> None:
    assert __version__ == "0.7.2"
    assert APP_TITLE == "2 week schedule generator"
    assert MILESTONE_LABEL == (
        "Milestone 4 AL/MC and SNF template export"
    )
    assert CANONICAL_FIELDS == (
        "employee_name",
        "shift_date",
        "start_time",
        "unit",
        "floor",
    )
