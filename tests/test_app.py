"""Streamlit smoke test for the Milestone 1 through 3 interface."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

import pandas as pd

from staffing_review.ui.layout import _schedule_template_kind


def test_app_starts_with_document_uploader_only() -> None:
    app_path = Path(__file__).parents[1] / "app.py"

    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "2 week schedule generator"
    assert len(app.get("file_uploader")) == 1
    assert len(app.dataframe) == 0
    assert len(app.get("download_button")) == 0
    assert len(app.metric) == 0
    assert len(app.button) == 0


def test_selects_template_from_reviewed_units() -> None:
    assert _schedule_template_kind(
        pd.DataFrame({"unit": ["Assisted Living", "Memory Care"]})
    ) == "al_mc"
    assert _schedule_template_kind(
        pd.DataFrame({"unit": ["Skilled Nursing"]})
    ) == "snf"
    assert _schedule_template_kind(
        pd.DataFrame({"unit": ["Assisted Living", "Skilled Nursing"]})
    ) is None
