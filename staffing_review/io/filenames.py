"""Consistent output filenames for two-week schedule artifacts."""

from datetime import timedelta

import pandas as pd


class OutlookFilenameError(ValueError):
    """Raised when a schedule date range cannot be determined."""


def outlook_filename(
    records: pd.DataFrame,
    department: str,
    extension: str,
) -> str:
    """Return the approved department and 14-day date-range filename."""
    valid_records = records
    statuses = records.get("validation_status")
    if statuses is not None:
        valid_records = records.loc[
            statuses.astype(str).str.strip().str.casefold() != "invalid"
        ]

    dates = pd.to_datetime(
        valid_records.get("shift_date", pd.Series(dtype=object)),
        errors="coerce",
    ).dropna()
    if dates.empty:
        raise OutlookFilenameError(
            "A valid shift date is required to name the schedule."
        )

    normalized_department = {
        "al_mc": "AL-MC",
        "al/mc": "AL-MC",
        "snf": "SNF",
    }.get(department.strip().casefold(), department.strip())
    start_date = dates.min().date()
    end_date = start_date + timedelta(days=13)
    suffix = extension.strip().lstrip(".")
    return (
        f"2 Week Outlook - {normalized_department} - "
        f"{start_date:%m.%d} to {end_date:%m.%d}.{suffix}"
    )
