"""Streamlit smoke test for the Milestone 1 through 3 interface."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

import pandas as pd

from staffing_review.ui.layout import _schedule_template_kind


def test_app_loads_synthetic_review_workflow() -> None:
    app_path = Path(__file__).parents[1] / "app.py"

    app = AppTest.from_file(str(app_path), default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "Staffing Schedule Review"
    assert len(app.get("file_uploader")) == 1
    assert len(app.dataframe) == 1
    assert len(app.get("download_button")) == 1
    assert [metric.value for metric in app.metric] == ["6", "6", "0"]


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
