"""Shared application constants."""

CANONICAL_FIELDS = (
    "employee_name",
    "shift_date",
    "start_time",
    "unit",
    "floor",
)

OPTIONAL_FIELDS = ("role",)

RECORD_FIELDS = (
    "employee_name",
    "role",
    "shift_date",
    "start_time",
    "unit",
    "floor",
)

REQUIRED_FIELDS = frozenset(CANONICAL_FIELDS)

REVIEW_COLUMNS = (
    "source_row",
    *RECORD_FIELDS,
    "validation_status",
    "validation_messages",
)

PDF_METADATA_COLUMNS = (
    "source_page",
    "extraction_confidence",
    "extraction_notes",
    "extraction_reviewed",
)

EXTRACTION_CONFIDENCE_THRESHOLD = 0.8

COLUMN_ALIASES = {
    "employee_name": (
        "employee_name",
        "employee name",
        "employee",
        "staff name",
        "staff",
        "name",
    ),
    "role": ("role", "primary job", "job", "position", "designation"),
    "shift_date": ("shift_date", "shift date", "date", "work date"),
    "start_time": (
        "start_time",
        "start time",
        "shift start",
        "shift start time",
        "start",
    ),
    "unit": ("unit", "care unit", "department"),
    "floor": ("floor", "level", "location floor"),
}

UNIT_ALIASES = {
    "al": "Assisted Living",
    "assisted living": "Assisted Living",
    "mc": "Memory Care",
    "memory care": "Memory Care",
    "snf": "Skilled Nursing",
    "skilled nursing": "Skilled Nursing",
}

VALID_UNITS = frozenset(UNIT_ALIASES.values())

SUPPORTED_FILE_TYPES = ("csv", "xlsx", "xls")
