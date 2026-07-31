"""Streamlit entry point for the staffing schedule review application."""

import streamlit as st

from staffing_review.config import APP_TITLE
from staffing_review.ui.layout import render_app


def main() -> None:
    """Configure and render the local review application."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=":material/calendar_month:",
        layout="wide",
    )
    render_app()


if __name__ == "__main__":
    main()
