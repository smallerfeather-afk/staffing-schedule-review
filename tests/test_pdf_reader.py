"""Synthetic regression tests for UKG weekly schedule PDF extraction."""

from io import BytesIO

import pytest
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

from staffing_review.io.pdf_reader import (
    PDFExtractionError,
    extract_ukg_schedule,
)
from staffing_review.services.review import review_records


def _synthetic_ukg_pdf(
    shift_cells: dict[int, tuple[str, str]],
    query: str = "Skilled Nursing",
    continuation_cells: dict[int, tuple[str, str]] | None = None,
) -> bytes:
    output = BytesIO()
    page = canvas.Canvas(output, pagesize=landscape(letter))
    width, height = landscape(letter)
    page.setFont("Helvetica", 9)
    page.drawString(36, height - 54, f"Query: {query}")

    x_positions = [36, 121, 171]
    for _ in range(7):
        x_positions.append(x_positions[-1] + 83)
    table_top = height - 90
    facility_bottom = table_top - 18
    header_bottom = facility_bottom - 42
    row_count = 2 if continuation_cells else 1
    table_bottom = header_bottom - (42 * row_count)

    horizontal_lines = [table_top, facility_bottom, header_bottom]
    horizontal_lines.extend(
        header_bottom - (42 * row)
        for row in range(1, row_count + 1)
    )
    for y in horizontal_lines:
        page.line(x_positions[0], y, x_positions[-1], y)
    page.line(x_positions[0], table_top, x_positions[0], table_bottom)
    page.line(x_positions[-1], table_top, x_positions[-1], table_bottom)
    for x in x_positions[1:-1]:
        page.line(x, facility_bottom, x, table_bottom)

    if query == "Skilled Nursing":
        facility = "Synthetic Community/Healthcare SNF/Default"
    elif query == "Assisted Living":
        facility = "Synthetic Community/Healthcare AL/WDI - AL3"
    elif query == "Memory Care":
        facility = "Synthetic Community/Healthcare MC/WDI - MC1"
    else:
        facility = "Synthetic Community/Default"
    page.drawString(
        x_positions[0] + 3,
        table_top - 13,
        facility,
    )
    page.drawString(x_positions[0] + 3, facility_bottom - 16, "Employee")
    page.drawString(x_positions[1] + 3, facility_bottom - 16, "Primary Job")

    headers = [
        "Fri 7/31/2026",
        "Sat 8/01/2026",
        "Sun 8/02/2026",
        "Mon 8/03/2026",
        "Tue 8/04/2026",
        "Wed 8/05/2026",
        "Thu 8/06/2026",
    ]
    for index, header in enumerate(headers):
        page.drawString(
            x_positions[index + 2] + 3,
            facility_bottom - 16,
            header,
        )

    page.drawString(x_positions[0] + 3, header_bottom - 16, "Avery Stone")
    page.drawString(x_positions[1] + 3, header_bottom - 16, "CNA")
    page.setFont("Helvetica", 7)
    for index, (time_range, location) in shift_cells.items():
        x = x_positions[index + 2] + 3
        page.drawString(x, header_bottom - 15, time_range)
        page.drawString(x, header_bottom - 29, location)

    for index, (time_range, location) in (continuation_cells or {}).items():
        x = x_positions[index + 2] + 3
        page.drawString(x, header_bottom - 57, time_range)
        page.drawString(x, header_bottom - 71, location)

    page.showPage()
    page.save()
    return output.getvalue()


def test_extracts_month_boundary_records_from_weekly_grid() -> None:
    payload = _synthetic_ukg_pdf(
        {
            0: ("7:00 PM - 7:00 AM", "WDI - S2 North/CNA"),
            1: ("7:00 AM - 3:00 PM", "WDI - S1 South/CNA"),
        }
    )

    extracted = extract_ukg_schedule(payload)
    reviewed = review_records(extracted)

    assert len(reviewed) == 2
    assert reviewed["employee_name"].tolist() == [
        "Avery Stone",
        "Avery Stone",
    ]
    assert reviewed["role"].tolist() == ["CNA", "CNA"]
    assert reviewed["shift_date"].tolist() == [
        "2026-07-31",
        "2026-08-01",
    ]
    assert reviewed["start_time"].tolist() == ["19:00", "07:00"]
    assert reviewed["unit"].tolist() == [
        "Skilled Nursing",
        "Skilled Nursing",
    ]
    assert reviewed["floor"].tolist() == ["S2 North", "S1 South"]
    assert reviewed["source_page"].tolist() == [1, 1]
    assert reviewed["extraction_confidence"].tolist() == [1.0, 1.0]
    assert reviewed["extraction_reviewed"].tolist() == [False, False]


def test_marks_unrecognized_layout_details_as_uncertain() -> None:
    payload = _synthetic_ukg_pdf(
        {0: ("Unknown shift", "Unstructured location")},
        query="Unrecognized Department",
    )

    reviewed = review_records(extract_ukg_schedule(payload))
    record = reviewed.iloc[0]

    assert record["extraction_confidence"] < 0.8
    assert "Start time was not recognized" in record["extraction_notes"]
    assert "Location prefix was not recognized" in record["extraction_notes"]
    assert "Care setting was not recognized" in record["extraction_notes"]
    assert record["validation_status"] == "Invalid"


@pytest.mark.parametrize(
    ("query", "floor", "expected_unit"),
    [
        ("Assisted Living", "AL3", "Assisted Living"),
        ("Memory Care", "MC1", "Memory Care"),
    ],
)
def test_classifies_al_mc_facility_headers(
    query: str,
    floor: str,
    expected_unit: str,
) -> None:
    payload = _synthetic_ukg_pdf(
        {0: ("7:00 AM - 3:00 PM", f"WDI - {floor}/Caregiver")},
        query=query,
    )

    reviewed = review_records(extract_ukg_schedule(payload))

    assert reviewed.loc[0, "unit"] == expected_unit
    assert reviewed.loc[0, "role"] == "Caregiver"
    assert reviewed.loc[0, "floor"] == floor
    assert reviewed.loc[0, "validation_status"] == "Valid"


def test_inherits_employee_and_primary_job_on_continuation_row() -> None:
    payload = _synthetic_ukg_pdf(
        {0: ("7:00 AM - 3:00 PM", "WDI - AL3/Caregiver")},
        query="Assisted Living",
        continuation_cells={
            1: ("3:00 PM - 11:00 PM", "WDI - AL3/Med Tech")
        },
    )

    reviewed = review_records(extract_ukg_schedule(payload))

    assert len(reviewed) == 2
    assert reviewed["employee_name"].tolist() == [
        "Avery Stone",
        "Avery Stone",
    ]
    assert reviewed["role"].tolist() == ["Caregiver", "Med Tech"]
    assert reviewed["validation_status"].tolist() == ["Valid", "Valid"]


def test_shift_floor_overrides_employee_facility_header() -> None:
    payload = _synthetic_ukg_pdf(
        {0: ("7:00 AM - 3:00 PM", "WDI - MC2/Caregiver")},
        query="Assisted Living",
    )

    reviewed = review_records(extract_ukg_schedule(payload))

    assert reviewed.loc[0, "unit"] == "Memory Care"


def test_rejects_non_pdf_content() -> None:
    with pytest.raises(PDFExtractionError, match="could not be read"):
        extract_ukg_schedule(b"not a PDF")
