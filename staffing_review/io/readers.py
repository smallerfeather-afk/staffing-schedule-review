"""Read supported schedule files into pandas DataFrames."""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from staffing_review.constants import SUPPORTED_FILE_TYPES


class ScheduleReadError(ValueError):
    """Raised when an uploaded schedule cannot be read safely."""


def read_file_bytes(file: BinaryIO) -> bytes:
    """Return uploaded bytes without relying on the current cursor position."""
    if hasattr(file, "getvalue"):
        return file.getvalue()

    file.seek(0)
    return file.read()


def read_schedule(file: BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Read one CSV or Excel schedule without mutating the source file."""
    resolved_name = filename or getattr(file, "name", "")
    extension = Path(resolved_name).suffix.lower().lstrip(".")

    if extension not in SUPPORTED_FILE_TYPES:
        allowed = ", ".join(f".{item}" for item in SUPPORTED_FILE_TYPES)
        raise ScheduleReadError(f"Unsupported file type. Choose {allowed}.")

    payload = read_file_bytes(file)
    if not payload:
        raise ScheduleReadError("The uploaded file is empty.")

    try:
        if extension == "csv":
            return _read_csv(payload)

        engine = "openpyxl" if extension == "xlsx" else "xlrd"
        return pd.read_excel(BytesIO(payload), engine=engine)
    except ScheduleReadError:
        raise
    except Exception as exc:
        raise ScheduleReadError(
            "The schedule could not be read. Confirm that the file is not "
            "password-protected or damaged."
        ) from exc


def _read_csv(payload: bytes) -> pd.DataFrame:
    last_error: UnicodeDecodeError | None = None

    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return pd.read_csv(BytesIO(payload), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc

    raise ScheduleReadError(
        "The CSV encoding is not supported. Save it as UTF-8 and try again."
    ) from last_error
