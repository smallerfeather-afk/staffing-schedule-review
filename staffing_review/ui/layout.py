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
from staffing_review.io.filenames import OutlookFilenameError, outlook_filename
from staffing_review.io.pdf_reader import PDFExtractionError, extract_ukg_schedule
from staffing_review.io.snf_template import (
    SNFTemplateError,
    export_snf_template,
    snf_template_filename,
)
from staffing_review.io.template_pdf import TemplatePDFError, export_template_pdf
from staffing_review.io.readers import (
    ScheduleReadError,
    read_file_bytes,
    read_schedule,
)
from staffing_review.services.mapping import MissingColumnsError
from staffing_review.services.review import prepare_source_records, review_records
from staffing_review.ui.review_table import render_review_table
from staffing_review.ui.summaries import render_validation_summary

_PRESERVE_SOURCE = object()


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


def _clear_records() -> None:
    st.session_state.review_records = None
    st.session_state.source_label = None
    st.session_state.source_workbook = None
    st.session_state.editor_revision = (
        st.session_state.get("editor_revision", 0) + 1
    )


def _initialize_state() -> None:
    st.session_state.setdefault("review_records", None)
    st.session_state.setdefault("source_label", None)
    st.session_state.setdefault("source_workbook", None)
    st.session_state.setdefault("editor_revision", 0)
    st.session_state.setdefault("upload_signature", None)
    st.session_state.setdefault("extraction_notice", None)


def _render_header() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background-color: var(--background-color);
            background:
              radial-gradient(
                circle at 88% 4%,
                color-mix(in srgb, #da973d 16%, transparent),
                transparent 30rem
              ),
              linear-gradient(
                180deg,
                color-mix(
                  in srgb,
                  var(--background-color) 95%,
                  var(--primary-color) 5%
                ) 0%,
                var(--background-color) 28rem
              );
            color: var(--text-color);
        }
        h1, h2, h3 {
            font-family: Georgia, "Times New Roman", serif;
            color: var(--text-color);
        }
        [data-testid="stMetric"] {
            background: color-mix(
              in srgb,
              var(--secondary-background-color) 88%,
              transparent
            );
            border: 1px solid color-mix(
              in srgb,
              var(--text-color) 18%,
              transparent
            );
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
        _clear_records()
        st.session_state.upload_signature = signature
        st.session_state.extraction_notice = None
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

    st.subheader("1. Upload a schedule")
    st.write(
        "Choose an AL/MC or SNF schedule document to begin. Review, "
        "validation, and download options will appear after processing."
    )
    uploaded_file = st.file_uploader(
        "Upload a CSV, Excel, or UKG PDF schedule",
        type=["csv", "xlsx", "xls", "pdf"],
        key="schedule_upload",
        help=(
            "CSV/Excel required columns: employee name, shift date, "
            "start time, unit, and floor; role is optional. PDF supports "
            "separate AL/MC and SNF UKG Employee Schedule - Weekly reports."
        ),
    )

    upload_error = _process_upload(uploaded_file) if uploaded_file else None
    if uploaded_file is None and st.session_state.upload_signature is not None:
        _clear_records()
        st.session_state.upload_signature = None
        st.session_state.extraction_notice = None
    if upload_error:
        st.error(upload_error, icon=":material/error:")
    if st.session_state.extraction_notice:
        st.warning(
            st.session_state.extraction_notice,
            icon=":material/warning:",
        )

    if st.session_state.review_records is None:
        return

    st.caption(f"Reviewing: **{st.session_state.source_label}**")
    st.subheader("2. Review and edit")
    st.write(
        "Edit values directly in the table. Validation updates below as you "
        "work. Use the button to normalize dates and times and restore "
        "chronological order. Shifts assigned to the Default location are "
        "excluded as non-floor staffing records."
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

    st.subheader("4. Generate 2 week outlook")
    st.write(
        "Download the populated operational template as Excel or PDF. "
        "Invalid rows are excluded from generated files."
    )
    template_kind = _schedule_template_kind(live_review)
    if template_kind == "al_mc":
        st.markdown("**AL/MC two-week template**")
        st.caption(
            "The approved blank template is stored in the application. "
            "Each download is a newly populated copy. Invalid rows are "
            "excluded from this operational template. The PDF uses two "
            "landscape 11 x 17 pages: Assisted Living first, then Memory "
            "Care."
        )
        try:
            template_bytes = export_al_mc_template(live_review)
            pdf_bytes = export_template_pdf(
                template_bytes,
                department="AL-MC",
            )
            excel_filename = al_mc_template_filename(live_review)
            pdf_filename = outlook_filename(live_review, "AL-MC", "pdf")
        except (
            ALMCTemplateError,
            OutlookFilenameError,
            TemplatePDFError,
        ) as exc:
            st.error(str(exc), icon=":material/error:")
        else:
            excel_column, pdf_column = st.columns(2)
            with excel_column:
                st.download_button(
                    "Download AL/MC Excel template",
                    data=template_bytes,
                    file_name=excel_filename,
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    type="primary",
                    icon=":material/download:",
                    use_container_width=True,
                )
            with pdf_column:
                st.download_button(
                    "Download AL/MC two-page PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    icon=":material/picture_as_pdf:",
                    use_container_width=True,
                )
    elif template_kind == "snf":
        st.markdown("**SNF two-week template**")
        st.caption(
            "The approved blank template is stored in the application. "
            "The UKG care setting automatically selected the SNF layout. "
            "Invalid rows are excluded from this operational template. "
            "The PDF fits the complete schedule on one landscape 11 x 17 "
            "page."
        )
        try:
            template_bytes = export_snf_template(live_review)
            pdf_bytes = export_template_pdf(
                template_bytes,
                department="SNF",
            )
            excel_filename = snf_template_filename(live_review)
            pdf_filename = outlook_filename(live_review, "SNF", "pdf")
        except (
            OutlookFilenameError,
            SNFTemplateError,
            TemplatePDFError,
        ) as exc:
            st.error(str(exc), icon=":material/error:")
        else:
            excel_column, pdf_column = st.columns(2)
            with excel_column:
                st.download_button(
                    "Download SNF Excel template",
                    data=template_bytes,
                    file_name=excel_filename,
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    type="primary",
                    icon=":material/download:",
                    use_container_width=True,
                )
            with pdf_column:
                st.download_button(
                    "Download SNF one-page PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    icon=":material/picture_as_pdf:",
                    use_container_width=True,
                )

    st.caption(
        "Files are downloaded locally only. Nothing is emailed, "
        "uploaded, or distributed automatically."
    )
