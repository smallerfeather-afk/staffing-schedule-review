"""Compose mapping, normalization, validation, and sorting."""

import pandas as pd

from staffing_review.constants import PDF_METADATA_COLUMNS, REVIEW_COLUMNS
from staffing_review.services.mapping import map_to_canonical
from staffing_review.services.normalization import normalize_records
from staffing_review.services.sorting import sort_records
from staffing_review.services.validation import validate_records


def prepare_source_records(data: pd.DataFrame) -> pd.DataFrame:
    """Prepare newly loaded source rows for the review table."""
    return review_records(map_to_canonical(data))


def review_records(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize, validate, sort, and stabilize review columns."""
    reviewed = validate_records(normalize_records(data))
    optional_columns = [
        column for column in PDF_METADATA_COLUMNS if column in reviewed.columns
    ]
    return sort_records(reviewed)[list(REVIEW_COLUMNS) + optional_columns]
