# UKG Weekly PDF Extraction

## Supported Report

The extractor targets the UKG `Employee Schedule - Weekly` PDF layout:

- landscape pages
- one weekly grid per page
- employee and primary-job columns
- seven dated day columns
- shift times inside populated day cells, with optional location overrides
- assigned neighborhood in the facility row immediately above the grid

The source PDF is processed in memory and is not stored by the application.
AL/MC and SNF reports can be uploaded separately; combining them is not
required.

## Canonical Mapping

| UKG value | Review field |
| --- | --- |
| Employee | `employee_name` |
| Role suffix in the shift cell, or Primary Job as fallback | `role` |
| Day-column date | `shift_date` |
| First time in the shift range | `start_time` |
| Query/facility care setting | `unit` |
| Shift location when present; otherwise the assigned neighborhood in the facility header | `floor` |
| PDF page | `source_page` |

One canonical record is created for each populated employee/day shift cell.
Blank continuation rows inherit the preceding employee and primary job while
retaining the role attached to that specific shift.

Time-only shifts inherit the neighborhood after the site prefix in the
facility header (for example, `Healthcare AL/WDI - AL1` supplies `AL1`).
The Primary Job supplies the role when no shift role is present. Calendar
locations and role suffixes override these defaults for that shift only;
start times always come from the calendar. The assigned neighborhood is
read separately on each page and never carried across page boundaries.

`Default` and `WDI- Default` headers do not identify an assigned neighborhood.
Time-only shifts under these headers remain flagged for missing location.
Unrecognized explicit calendar locations remain flagged for review rather
than being silently replaced by the header's neighborhood. Older reports
with explicit locations in every shift continue to use those locations.

For the AL/MC two-week template, the shift's floor prefix determines its
destination section even when the employee's facility header differs.
Additional names beyond a template slot's normal capacity are appended to the
last applicable cell on wrapped lines; they are never discarded.

The approved blank AL/MC workbook is bundled with the local application.
Available cells without an assigned shift display `OPEN` in bold red. Filled
AM cells use regular black text, filled PM cells use regular white text, and
only blocked `XXXXXXXXXXXX` cells use yellow text. Schedule rows and columns
use fixed dimensions so wrapped names remain readable without manual resizing.

The approved blank SNF workbook is also bundled with the application. CNA
shifts map to the exact James, James/Johns, Johns, Folly, Folly/Morris, or
Morris row. LPN and RN shifts map to the nurse hall rows. RN names use purple
font without an appended role label. When Folly is OPEN for a PM nurse shift
and Morris has named coverage, the Folly and Morris PM cells merge and show
only the Morris nurse names. Both template types are selected automatically
from the reviewed record units.

Rows with `Invalid` validation status remain visible in the review workflow
and generic review workbook, but are excluded from populated AL/MC and SNF
operational templates.

## Confidence Rules

Extraction begins at `1.00`. Confidence is reduced when:

- the date header cannot be parsed
- the start time cannot be parsed
- multiple shift ranges appear in one cell
- neither a shift location nor an assigned neighborhood is available, or an
  explicit shift location does not match the expected prefix
- the employee name is absent
- the care setting cannot be identified

Records below `0.80` remain editable and appear in the manual-review queue.
The scheduler can check `extraction_reviewed` after confirming the row.

## De-identified Benchmark

The supplied local reference reports were not copied into the repository.
Privacy-safe aggregate comparison produced:

- SNF: 202 records across 14 dates, with 105 CNA, 75 LPN, and 22 RN shifts
- SNF: 10 records with missing location/floor values routed to manual review
- AL/MC: 372 records across 14 dates
- AL/MC: 264 Assisted Living and 108 Memory Care shifts
- AL/MC: 237 Caregiver and 135 Med Tech shifts
- AL/MC: no invalid or uncertain extractions in the supplied example

No employee names or source roster data are stored in this document or in
automated fixtures.
