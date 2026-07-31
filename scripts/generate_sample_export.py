"""Generate a synthetic Milestone 3 workbook for manual QA."""

from pathlib import Path

import pandas as pd

from staffing_review.io.exporters import export_reviewed_schedule
from staffing_review.services.review import prepare_source_records, review_records

PROJECT_ROOT = Path(__file__).parents[1]
SAMPLE_PATH = PROJECT_ROOT / "sample_data" / "synthetic_schedule_valid.csv"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "synthetic_schedule_reviewed.xlsx"


def main() -> None:
    source = pd.read_csv(SAMPLE_PATH)
    records = prepare_source_records(source)
    records.loc[0, "employee_name"] = "OPEN"
    records.loc[1, "floor"] = "#2"
    reviewed = review_records(records)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(export_reviewed_schedule(reviewed))
    print(OUTPUT_PATH.resolve())


if __name__ == "__main__":
    main()
