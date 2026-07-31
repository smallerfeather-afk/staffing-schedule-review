"""Validation summary components."""

import pandas as pd
import streamlit as st

from staffing_review.constants import EXTRACTION_CONFIDENCE_THRESHOLD
from staffing_review.services.validation import summarize_validation


def render_validation_summary(data: pd.DataFrame) -> None:
    """Show review counts and focused details for invalid rows."""
    summary = summarize_validation(data)
    total_col, valid_col, invalid_col = st.columns(3)
    total_col.metric("Records", summary.total)
    valid_col.metric("Valid", summary.valid)
    invalid_col.metric("Needs review", summary.invalid)

    if summary.invalid:
        st.warning(
            f"{summary.invalid} record(s) need attention before export.",
            icon=":material/warning:",
        )
        invalid_rows = data.loc[
            data["validation_status"] == "Invalid",
            ["source_row", "employee_name", "validation_messages"],
        ]
        with st.expander("Show records needing review", expanded=True):
            st.dataframe(invalid_rows, hide_index=True, width="stretch")
    else:
        st.success(
            "All displayed records pass the current review checks.",
            icon=":material/check_circle:",
        )

    if "extraction_confidence" not in data.columns:
        return

    reviewed = data.get("extraction_reviewed", False)
    if not isinstance(reviewed, pd.Series):
        reviewed = pd.Series(False, index=data.index)
    unresolved = (
        data["extraction_confidence"].fillna(0)
        < EXTRACTION_CONFIDENCE_THRESHOLD
    ) & ~reviewed.fillna(False).astype(bool)
    uncertain_count = int(unresolved.sum())

    if uncertain_count:
        st.warning(
            f"{uncertain_count} PDF extraction(s) require manual confirmation.",
            icon=":material/visibility:",
        )
        columns = [
            "source_page",
            "employee_name",
            "shift_date",
            "start_time",
            "extraction_confidence",
            "extraction_notes",
        ]
        with st.expander("Show uncertain PDF extractions", expanded=True):
            st.dataframe(
                data.loc[unresolved, columns],
                hide_index=True,
                width="stretch",
            )
    else:
        st.success(
            "All uncertain PDF extractions have been reviewed.",
            icon=":material/fact_check:",
        )
