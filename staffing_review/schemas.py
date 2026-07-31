"""Small schema helpers shared by ingest and review services."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationSummary:
    """Aggregate row validation counts."""

    total: int
    valid: int
    invalid: int
