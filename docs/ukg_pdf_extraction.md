# UKG Weekly PDF Extraction

## Supported Report

The extractor targets the UKG `Employee Schedule - Weekly` PDF layout:

- landscape pages
- one weekly grid per page
- employee and primary-job columns
- seven dated day columns
- shift time and location text inside populated day cells

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
| Location after the site prefix and before the role suffix | `floor` |
| PDF page | `source_page` |

One canonical record is created for each populated employee/day shift cell.
Blank continuation rows inherit the preceding employee and primary job while
retaining the role attached to that specific shift.

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
- the location is absent or does not match the expected prefix
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
