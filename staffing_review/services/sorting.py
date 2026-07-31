"""Stable chronological sorting for reviewed schedule records."""

import pandas as pd


def sort_records(data: pd.DataFrame) -> pd.DataFrame:
    """Sort valid dates/times first and leave invalid values at the end."""
    sortable = data.copy()
    sortable["_sort_date"] = pd.to_datetime(
        sortable["shift_date"], format="%Y-%m-%d", errors="coerce"
    )
    sortable["_sort_time"] = pd.to_datetime(
        sortable["start_time"], format="%H:%M", errors="coerce"
    )
    sortable["_sort_name"] = sortable["employee_name"].astype(str).str.casefold()

    return (
        sortable.sort_values(
            ["_sort_date", "_sort_time", "_sort_name"],
            kind="stable",
            na_position="last",
        )
        .drop(columns=["_sort_date", "_sort_time", "_sort_name"])
        .reset_index(drop=True)
    )
