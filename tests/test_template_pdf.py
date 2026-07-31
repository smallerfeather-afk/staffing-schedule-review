"""Tests for schedule-template PDF export."""

from io import BytesIO

from pypdf import PdfReader

from staffing_review.io.al_mc_template import export_al_mc_template
from staffing_review.io.snf_template import export_snf_template
from staffing_review.io.template_pdf import PAGE_MARGIN, PAGE_SIZE, export_template_pdf

from tests.test_al_mc_template import _records, _template_bytes
from tests.test_snf_template import _records as _snf_records


def test_exports_al_mc_as_two_complete_landscape_pages() -> None:
    workbook_bytes = export_al_mc_template(_records(), _template_bytes())
    payload = export_template_pdf(workbook_bytes, department="AL-MC")
    reader = PdfReader(BytesIO(payload))

    assert len(reader.pages) == 2
    for page in reader.pages:
        assert float(page.mediabox.width) == PAGE_SIZE[0]
        assert float(page.mediabox.height) == PAGE_SIZE[1]
        assert float(page.mediabox.width) > float(page.mediabox.height)
    assisted_living_text = reader.pages[0].extract_text()
    memory_care_text = reader.pages[1].extract_text()
    assert "Assisted Living" in assisted_living_text
    assert "Memory Care" not in assisted_living_text
    assert "AM Med Tech" in assisted_living_text
    assert "Memory Care" in memory_care_text
    assert "Assisted Living" not in memory_care_text
    assert "Week Two" in memory_care_text
    assert assisted_living_text.count("OPEN") == 206
    assert memory_care_text.count("OPEN") == 167
    assert assisted_living_text.count("XXXXXXXXXXXX") == 42
    assert memory_care_text.count("XXXXXXXXXXXX") == 28
    assert PAGE_MARGIN <= 7.2


def test_keeps_snf_on_one_landscape_page() -> None:
    workbook_bytes = export_snf_template(_snf_records())
    payload = export_template_pdf(workbook_bytes, department="SNF")
    reader = PdfReader(BytesIO(payload))

    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "CNA Schedule" in text
    assert "Nurses Schedule" in text
