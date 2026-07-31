"""Map common source headers into the canonical review schema."""

import re

import pandas as pd

from staffing_review.constants import (
    COLUMN_ALIASES,
    RECORD_FIELDS,
    REQUIRED_FIELDS,
)


class MissingColumnsError(ValueError):
    """Raised when required schedule columns cannot be identified."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        labels = ", ".join(field.replace("_", " ") for field in missing)
        super().__init__(f"Missing required columns: {labels}.")


def normalize_header(value: object) -> str:
    """Create a stable comparison key from a source column heading."""
    text = str(value).strip().casefold()
    return re.sub(r"[\s_-]+", " ", text)


def resolve_column_mapping(columns: pd.Index) -> dict[object, str]:
    """Resolve source headers to canonical field names."""
    aliases = {
        normalize_header(alias): canonical
        for canonical, options in COLUMN_ALIASES.items()
        for alias in options
    }
    mapping: dict[object, str] = {}
    resolved: set[str] = set()

    for column in columns:
        canonical = aliases.get(normalize_header(column))
        if canonical and canonical not in resolved:
            mapping[column] = canonical
            resolved.add(canonical)

    missing = sorted(REQUIRED_FIELDS - resolved)
    if missing:
        raise MissingColumnsError(missing)

    return mapping


def map_to_canonical(data: pd.DataFrame) -> pd.DataFrame:
    """Return required schedule fields plus a traceable source row."""
    mapping = resolve_column_mapping(data.columns)
    renamed = data.rename(columns=mapping)
    for field in RECORD_FIELDS:
        if field not in renamed.columns:
            renamed[field] = ""
    canonical = renamed[list(RECORD_FIELDS)].copy()
    canonical.insert(0, "source_row", range(2, len(canonical) + 2))
    return canonical
