"""Print privacy-safe aggregate extraction checks for a UKG schedule PDF."""

import argparse
from pathlib import Path

from staffing_review.constants import EXTRACTION_CONFIDENCE_THRESHOLD
from staffing_review.io.pdf_reader import extract_ukg_schedule
from staffing_review.services.review import review_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()

    records = review_records(extract_ukg_schedule(args.pdf.read_bytes()))
    uncertain = (
        records["extraction_confidence"] < EXTRACTION_CONFIDENCE_THRESHOLD
    )
    print(
        {
            "records": len(records),
            "date_min": records["shift_date"].min(),
            "date_max": records["shift_date"].max(),
            "unique_dates": records["shift_date"].nunique(),
            "invalid_records": int(
                (records["validation_status"] == "Invalid").sum()
            ),
            "uncertain_records": int(uncertain.sum()),
            "source_pages": records["source_page"].nunique(),
        }
    )


if __name__ == "__main__":
    main()
