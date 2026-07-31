"""Extract canonical staffing records from UKG weekly schedule PDFs."""

from io import BytesIO
import re

import pandas as pd
import pdfplumber

from staffing_review.constants import PDF_METADATA_COLUMNS, RECORD_FIELDS

TABLE_SETTINGS = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "join_tolerance": 3,
    "intersection_tolerance": 3,
}

DATE_PATTERN = re.compile(r"(\d{1,2}/\d{1,2}/\d{4})")
TIME_RANGE_PATTERN = re.compile(
    r"(?P<start>\d{1,2}:\d{2}\s*[AP]M)\s*-\s*"
    r"(?P<end>\d{1,2}:\d{2}\s*[AP]M)",
    re.IGNORECASE,
)


class PDFExtractionError(ValueError):
    """Raised when a PDF is not a supported UKG weekly schedule."""


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _infer_unit(text: str) -> str:
    lowered = text.casefold()
    if "skilled nursing" in lowered or "healthcare snf" in lowered:
        return "Skilled Nursing"
    if "memory care" in lowered or "healthcare mc" in lowered:
        return "Memory Care"
    if "assisted living" in lowered or "healthcare al" in lowered:
        return "Assisted Living"
    return ""


def _unit_from_floor(floor: str, fallback: str) -> str:
    normalized = floor.strip().casefold()
    if normalized.startswith("al"):
        return "Assisted Living"
    if normalized.startswith("mc"):
        return "Memory Care"
    return fallback


def _extract_role(shift_text: str, primary_job: str) -> str:
    lines = [line.strip() for line in shift_text.splitlines() if line.strip()]
    location = " ".join(
        line for line in lines if not TIME_RANGE_PATTERN.search(line)
    )
    suffix = re.search(r"/\s*([^/]+?)\s*$", location)
    return _clean(suffix.group(1)) if suffix else primary_job


def _extract_floor(shift_text: str, role: str) -> tuple[str, str | None]:
    lines = [line.strip() for line in shift_text.splitlines() if line.strip()]
    time_line_index = next(
        (index for index, line in enumerate(lines) if TIME_RANGE_PATTERN.search(line)),
        None,
    )
    location_lines = (
        lines[time_line_index + 1 :] if time_line_index is not None else lines[1:]
    )
    location = " ".join(location_lines).strip()
    if not location:
        return "", "Location was not found"

    role_suffix = re.compile(rf"/\s*{re.escape(role)}\s*$", re.IGNORECASE)
    location = role_suffix.sub("", location).strip()
    if " - " in location:
        location = location.split(" - ", 1)[1].strip()
    else:
        return location, "Location prefix was not recognized"

    return location, None


def _extract_shift(
    employee_name: str,
    primary_job: str,
    date_header: str,
    shift_text: str,
    unit: str,
    page_number: int,
    source_row: int,
) -> dict[str, object]:
    notes: list[str] = []
    confidence = 1.0
    role = _extract_role(shift_text, primary_job)

    date_match = DATE_PATTERN.search(date_header)
    shift_date = date_match.group(1) if date_match else _clean(date_header)
    if not date_match:
        confidence -= 0.4
        notes.append("Date header was not recognized")

    time_matches = list(TIME_RANGE_PATTERN.finditer(shift_text))
    if time_matches:
        start_time = _clean(time_matches[0].group("start"))
        if len(time_matches) > 1:
            confidence -= 0.25
            notes.append("Multiple shift ranges were found in one cell")
    else:
        start_time = _clean(shift_text.splitlines()[0] if shift_text else "")
        confidence -= 0.4
        notes.append("Start time was not recognized")

    floor, floor_note = _extract_floor(shift_text, role)
    unit = _unit_from_floor(floor, unit)
    if floor_note:
        confidence -= 0.25
        notes.append(floor_note)

    if not employee_name:
        confidence -= 0.25
        notes.append("Employee name was not found")
    if not unit:
        confidence -= 0.25
        notes.append("Care setting was not recognized")

    return {
        "source_row": source_row,
        "employee_name": employee_name,
        "role": role,
        "shift_date": shift_date,
        "start_time": start_time,
        "unit": unit,
        "floor": floor,
        "source_page": page_number,
        "extraction_confidence": round(max(confidence, 0.0), 2),
        "extraction_notes": "; ".join(notes),
        "extraction_reviewed": False,
    }


def _find_header_row(table: list[list[object]]) -> int | None:
    for index, row in enumerate(table):
        if row and _clean(row[0]).casefold() == "employee":
            return index
    return None


def extract_ukg_schedule(payload: bytes) -> pd.DataFrame:
    """Extract one record per populated employee/day shift cell."""
    if not payload:
        raise PDFExtractionError("The uploaded PDF is empty.")

    records: list[dict[str, object]] = []
    unsupported_pages: list[int] = []

    try:
        with pdfplumber.open(BytesIO(payload)) as pdf:
            if not pdf.pages:
                raise PDFExtractionError("The uploaded PDF has no pages.")

            for page_number, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables(TABLE_SETTINGS)
                candidates = [
                    table
                    for table in tables
                    if table and _find_header_row(table) is not None
                ]
                if not candidates:
                    unsupported_pages.append(page_number)
                    continue

                table = max(
                    candidates,
                    key=lambda candidate: len(candidate)
                    * max(len(row) for row in candidate),
                )
                header_index = _find_header_row(table)
                if header_index is None:
                    unsupported_pages.append(page_number)
                    continue

                header = table[header_index]
                page_text = page.extract_text() or ""
                unit = _infer_unit(page_text)
                current_employee = ""
                current_primary_job = ""

                for row in table[header_index + 1 :]:
                    if len(row) < 3:
                        continue
                    row_employee = _clean(row[0])
                    row_primary_job = _clean(row[1])
                    if row_employee:
                        current_employee = row_employee
                    if row_primary_job:
                        current_primary_job = row_primary_job
                    employee_name = row_employee or current_employee
                    primary_job = row_primary_job or current_primary_job

                    for column in range(2, min(len(row), len(header))):
                        shift_text = str(row[column] or "").strip()
                        if not shift_text:
                            continue
                        records.append(
                            _extract_shift(
                                employee_name=employee_name,
                                primary_job=primary_job,
                                date_header=str(header[column] or ""),
                                shift_text=shift_text,
                                unit=unit,
                                page_number=page_number,
                                source_row=len(records) + 2,
                            )
                        )
    except PDFExtractionError:
        raise
    except Exception as exc:
        raise PDFExtractionError(
            "The PDF could not be read. Confirm that it is an unencrypted "
            "UKG Employee Schedule - Weekly report."
        ) from exc

    if not records:
        raise PDFExtractionError(
            "No schedule records were found. Confirm that this is a UKG "
            "Employee Schedule - Weekly report."
        )

    result = pd.DataFrame(records)
    result.attrs["unsupported_pages"] = unsupported_pages
    return result[
        [
            "source_row",
            *RECORD_FIELDS,
            *PDF_METADATA_COLUMNS,
        ]
    ]
