"""Main Streamlit layout for schedule upload and review."""

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from staffing_review.config import APP_CAPTION, APP_TITLE
from staffing_review.io.al_mc_template import (
    ALMCTemplateError,
    al_mc_template_filename,
    export_al_mc_template,
)
from staffing_review.io.exporters import export_filename, export_reviewed_schedule
from staffing_review.io.pdf_reader import PDFExtractionError, extract_ukg_schedule
from staffing_review.io.snf_template import (
    SNFTemplateError,
    export_snf_template,
    snf_template_filename,
)
from staffing_review.io.readers import (
    ScheduleReadError,
    read_file_bytes,
    read_schedule,
)
from staffing_review.services.mapping import MissingColumnsError
from staffing_review.services.review import prepare_source_records, review_records
from staffing_review.ui.review_table import render_review_table
from staffing_review.ui.summaries import render_validation_summary

SAMPLE_PATH = Path(__file__).parents[2] / "sample_data" / "synthetic_schedule_valid.csv"
_PRESERVE_SOURCE = object()


def _load_sample() -> pd.DataFrame:
    with SAMPLE_PATH.open("rb") as sample_file:
        return prepare_source_records(
            read_schedule(sample_file, filename=SAMPLE_PATH.name)
        )


def _set_records(
    records: pd.DataFrame,
    source_label: str,
    source_workbook: bytes | None | object = _PRESERVE_SOURCE,
) -> None:
    st.session_state.review_records = records
    st.session_state.source_label = source_label
    if source_workbook is not _PRESERVE_SOURCE:
        st.session_state.source_workbook = source_workbook
    st.session_state.editor_revision = (
        st.session_state.get("editor_revision", 0) + 1
    )


def _initialize_state() -> None:
    if "review_records" not in st.session_state:
        _set_records(_load_sample(), "Synthetic sample schedule", None)
    st.session_state.setdefault("upload_signature", None)
    st.session_state.setdefault("upload_revision", 0)
    st.session_state.setdefault("extraction_notice", None)


def _render_header() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
              radial-gradient(circle at 88% 4%, rgba(218, 151, 61, .14), transparent 30rem),
              linear-gradient(180deg, #f6f3ec 0%, #fbfaf7 28rem);
        }
        h1, h2, h3 { font-family: Georgia, "Times New Roman", serif; color: #183a35; }
        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, .72);
            border: 1px solid #d8d1c3;
            border-radius: 10px;
            padding: .75rem 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title(APP_TITLE)
    st.caption(APP_CAPTION)
    st.markdown(
        "`LOCAL ONLY`  Files stay in this running application and are never "
        "emailed or distributed automatically."
    )


def _schedule_template_kind(records: pd.DataFrame) -> str | None:
    units = {
        str(value)
        for value in records.get("unit", pd.Series(dtype=str)).dropna()
        if str(value).strip()
    }
    if units and units.issubset({"Assisted Living", "Memory Care"}):
        return "al_mc"
    if units == {"Skilled Nursing"}:
        return "snf"
    return None


def _process_upload(uploaded_file: object) -> str | None:
    signature = (
        getattr(uploaded_file, "name", ""),
        getattr(uploaded_file, "size", None),
    )
    if signature == st.session_state.upload_signature:
        return None

    try:
        filename = getattr(uploaded_file, "name", "")
        payload = read_file_bytes(uploaded_file)
        if Path(filename).suffix.casefold() == ".pdf":
            extracted = extract_ukg_schedule(payload)
            reviewed = review_records(extracted)
            unsupported_pages = extracted.attrs.get("unsupported_pages", [])
            st.session_state.extraction_notice = (
                f"{len(unsupported_pages)} page(s) did not contain a "
                "recognized weekly schedule table."
                if unsupported_pages
                else None
            )
        else:
            source = read_schedule(BytesIO(payload), filename=filename)
            reviewed = prepare_source_records(source)
            st.session_state.extraction_notice = None
    except (PDFExtractionError, ScheduleReadError, MissingColumnsError) as exc:
        st.session_state.upload_signature = signature
        return str(exc)

    source_workbook = payload if Path(filename).suffix.casefold() == ".xlsx" else None
    _set_records(
        reviewed,
        filename or "Uploaded schedule",
        source_workbook,
    )
    st.session_state.upload_signature = signature
    return None


def render_app() -> None:
    """Render the local review, export, and UKG PDF workflow."""
    _initialize_state()
    _render_header()

    st.subheader("1. Choose a schedule")
    upload_col, sample_col = st.columns([3, 1], vertical_alignment="bottom")
    with upload_col:
        uploaded_file = st.file_uploader(
            "Upload a CSV, Excel, or UKG PDF schedule",
            type=["csv", "xlsx", "xls", "pdf"],
            key=f"schedule_upload_{st.session_state.upload_revision}",
            help=(
                "CSV/Excel required columns: employee name, shift date, "
                "start time, unit, and floor; role is optional. PDF supports "
                "separate AL/MC and SNF UKG Employee Schedule - Weekly "
                "reports."
            ),
        )
    with sample_col:
        if st.button("Restore synthetic sample", width="stretch"):
            _set_records(_load_sample(), "Synthetic sample schedule", None)
            st.session_state.upload_signature = None
            st.session_state.extraction_notice = None
            st.session_state.upload_revision += 1
            st.rerun()

    upload_error = _process_upload(uploaded_file) if uploaded_file else None
    if upload_error:
        st.error(upload_error, icon=":material/error:")
    if st.session_state.extraction_notice:
        st.warning(
            st.session_state.extraction_notice,
            icon=":material/warning:",
        )

    st.caption(f"Reviewing: **{st.session_state.source_label}**")
    st.subheader("2. Review and edit")
    st.write(
        "Edit values directly in the table. Validation updates below as you "
        "work. Use the button to normalize dates and times and restore "
        "chronological order."
    )

    edited = render_review_table(
        st.session_state.review_records,
        key=f"schedule_editor_{st.session_state.editor_revision}",
    )
    live_review = review_records(edited)

    if st.button(
        "Normalize and sort records",
        type="primary",
        icon=":material/sort:",
    ):
        _set_records(live_review, st.session_state.source_label)
        st.rerun()

    st.subheader("3. Validation summary")
    render_validation_summary(live_review)

    st.subheader("4. Export cleaned workbook")
    st.write(
        "Download the current reviewed records as an Excel workbook. Invalid "
        "rows are highlighted red and open shifts are highlighted amber."
    )
    export_bytes = export_reviewed_schedule(
        live_review,
        st.session_state.get("source_workbook"),
    )
    template_kind = _schedule_template_kind(live_review)
    if template_kind == "al_mc":
        st.markdown("**AL/MC two-week template**")
        st.caption(
            "The approved blank template is stored in the application. "
            "Each download is a newly populated copy. Invalid rows are "
            "excluded from this operational template."
        )
        try:
            template_bytes = export_al_mc_template(live_review)
        except ALMCTemplateError as exc:
            st.error(str(exc), icon=":material/error:")
        else:
            st.download_button(
                "Download populated AL/MC template",
                data=template_bytes,
                file_name=al_mc_template_filename(
                    st.session_state.source_label
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                type="primary",
                icon=":material/download:",
            )
    elif template_kind == "snf":
        st.markdown("**SNF two-week template**")
        st.caption(
            "The approved blank template is stored in the application. "
            "The UKG care setting automatically selected the SNF layout. "
            "Invalid rows are excluded from this operational template."
        )
        try:
            template_bytes = export_snf_template(live_review)
        except SNFTemplateError as exc:
            st.error(str(exc), icon=":material/error:")
        else:
            st.download_button(
                "Download populated SNF template",
                data=template_bytes,
                file_name=snf_template_filename(
                    st.session_state.source_label
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                type="primary",
                icon=":material/download:",
            )

    st.download_button(
        "Download generic review workbook",
        data=export_bytes,
        file_name=export_filename(st.session_state.source_label),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        icon=":material/download:",
    )
    st.caption(
        "The workbook is downloaded locally only. Nothing is emailed, "
        "uploaded, or distributed automatically."
    )
