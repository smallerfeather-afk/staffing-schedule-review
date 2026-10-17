# Staffing Schedule Review

A local Streamlit application for reviewing staffing schedule exports.
Milestones 1 through 5 are complete, including the approved AL/MC and SNF
two-week template workflows.

The application is designed for local, manual use. It does not email, publish,
or distribute information.

## Requirements

- Windows
- Python 3.10 or newer
- PowerShell

## Local Setup

From the `staffing_schedule_review` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents virtual-environment activation, the same commands can be
run without activation:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the Application

With the virtual environment active:

```powershell
python -m streamlit run app.py
```

Streamlit will print a local address, normally `http://localhost:8501`.

## Run Tests

```powershell
python -m pytest
```

## Current Scope

Available now:

- local CSV, `.xlsx`, and `.xls` schedule upload
- common source-header mapping and required-column validation
- document-first interface that reveals review tools after upload
- editable schedule records
- date and start-time normalization
- assisted living, memory care, and skilled nursing unit validation
- optional per-shift role extraction and editing
- floor validation
- automatic exclusion of non-floor shifts with location `Default`
- row-level validation messages and summary counts
- chronological sorting
- UKG `Employee Schedule - Weekly` PDF extraction
- confidence scores, source-page traceability, and extraction notes
- manual confirmation checkboxes for uncertain PDF records
- two-page AL/MC and one-page SNF landscape PDF output

## Required Schedule Fields

The app recognizes common header variations for:

- employee name
- shift date
- start time
- unit
- floor

Role is optional for CSV and Excel uploads. Supported UKG PDFs derive the role
from each shift cell, falling back to the employee's primary job when needed.
Unit values can use the full care-setting name or `AL`, `MC`, and `SNF`.
Floor labels may be numeric or text, such as `1`, `2A`, or `Ground`.
For UKG PDFs, time-only calendar shifts use the employee's assigned
neighborhood from the facility header. An explicit calendar location takes
precedence for that shift. Generic `Default` headers still require an
explicit shift location or manual correction.

## Review Workflow

1. Upload one local CSV, Excel, or supported UKG PDF schedule.
2. Correct records directly in the review table.
3. Review live validation counts and row-level messages.
4. Select **Normalize and sort records** to standardize dates and times and
   restore chronological order.
5. Download the populated operational template as Excel or PDF.

For a UKG PDF, review records with extraction confidence below `0.80` and
check **Extraction reviewed** after confirming each uncertain row.
Upload and export the AL/MC and SNF reports separately; combining the source
PDFs is not required.

## Operational Export

Invalid records remain visible in the review table for correction but are
excluded from populated AL/MC and SNF operational templates. Downloads are
manual and local; the application does not email, upload, or distribute files.

The approved AL/MC and SNF blank two-week templates are stored in the
application. The app automatically selects the matching template when the
reviewed schedule contains only AL/MC units or only Skilled Nursing records.
Shifts are mapped by date, AM/PM start period, floor, and role. Empty available
cells display `OPEN` in bold red, AM names use regular black text, PM names use
regular white text, and only blocked `XXXXXXXXXXXX` cells use yellow text.
Additional names are stacked on separate wrapped lines.

SNF CNA shifts map to the exact source hall row. LPN and RN shifts map to the
nurse section, with RN names shown in purple and without a role suffix. When a
Folly PM nurse slot is OPEN and Morris has named coverage, those two PM cells
are merged and display only the Morris nurse names.

Each populated operational template is available as Excel and as a vector PDF
with landscape 11 x 17-inch pages and 0.1-inch margins. The AL/MC PDF contains
two pages for readability: Assisted Living on page 1 and Memory Care on page
2. The SNF PDF contains the complete template on one page. Both formats use
the filename pattern
`2 Week Outlook - AL-MC - MM.DD to MM.DD` or
`2 Week Outlook - SNF - MM.DD to MM.DD`. The date range always represents the
full 14-day template period.

## UKG PDF Processing

The PDF extractor supports the observed UKG weekly employee-grid layout. It
creates one row per populated employee/day cell and retains the source page,
per-shift role, confidence score, extraction notes, and manual-review state.
AL/MC and SNF source reports are handled as separate uploads. Uploaded PDFs
and extracted data remain in the running local session and are not written to
the project.

See `docs/ukg_pdf_extraction.md` for mapping and privacy-safe benchmark details.

## Planning Documents

The approved product specification and implementation plan remain in the
workspace root:

- `../PRODUCT_SPEC.md`
- `../IMPLEMENTATION_PLAN.md`
