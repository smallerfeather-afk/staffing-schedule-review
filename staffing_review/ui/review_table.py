"""Editable Streamlit schedule review table."""

import pandas as pd
import streamlit as st

from staffing_review.constants import PDF_METADATA_COLUMNS, RECORD_FIELDS


def render_review_table(data: pd.DataFrame, key: str) -> pd.DataFrame:
    """Render editable schedule fields and locked trace/validation fields."""
    optional_columns = [
        column for column in PDF_METADATA_COLUMNS if column in data.columns
    ]
    disabled_columns = [
        "source_row",
        "validation_status",
        "validation_messages",
        "source_page",
        "extraction_confidence",
        "extraction_notes",
    ]
    return st.data_editor(
        data,
        key=key,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        disabled=[
            column for column in disabled_columns if column in data.columns
        ],
        column_order=[
            "source_row",
            *RECORD_FIELDS,
            "validation_status",
            "validation_messages",
            *optional_columns,
        ],
        column_config={
            "source_row": st.column_config.NumberColumn(
                "Source row", help="Original row in the uploaded file."
            ),
            "employee_name": st.column_config.TextColumn(
                "Employee name", required=True
            ),
            "role": st.column_config.TextColumn(
                "Role",
                help="Examples: CNA, Caregiver, Med Tech, LPN, or RN.",
            ),
            "shift_date": st.column_config.TextColumn(
                "Shift date", help="Use YYYY-MM-DD.", required=True
            ),
            "start_time": st.column_config.TextColumn(
                "Start time", help="Use HH:MM or a familiar AM/PM time.", required=True
            ),
            "unit": st.column_config.TextColumn(
                "Unit",
                help="Assisted Living, Memory Care, or Skilled Nursing.",
                required=True,
            ),
            "floor": st.column_config.TextColumn(
                "Floor", help="Examples: 1, 2A, Ground.", required=True
            ),
            "validation_status": st.column_config.TextColumn("Status"),
            "validation_messages": st.column_config.TextColumn(
                "Validation details", width="large"
            ),
            "source_page": st.column_config.NumberColumn(
                "PDF page", help="Source page in the uploaded UKG report."
            ),
            "extraction_confidence": st.column_config.NumberColumn(
                "Extraction confidence",
                help="Values below 0.80 require manual confirmation.",
                format="%.2f",
            ),
            "extraction_notes": st.column_config.TextColumn(
                "Extraction notes", width="large"
            ),
            "extraction_reviewed": st.column_config.CheckboxColumn(
                "Extraction reviewed",
                help="Check after confirming an uncertain PDF extraction.",
            ),
        },
    )
