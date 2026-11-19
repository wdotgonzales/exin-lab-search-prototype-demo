"""Spreadsheet files as plain tables, for the document page's table view."""

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from openpyxl import load_workbook

MAX_ROWS = 500
MAX_COLS = 50


class TableError(Exception):
    """The file could not be read as a table."""


@dataclass
class Sheet:
    name: str
    rows: list[list[str]]
    truncated: bool


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _take(rows, name: str) -> Sheet:
    out: list[list[str]] = []
    truncated = False
    for row in rows:
        if len(out) == MAX_ROWS:
            truncated = True
            break
        cells = [_cell(v) for v in row[:MAX_COLS]]
        truncated = truncated or len(row) > MAX_COLS
        out.append(cells)
    # drop trailing empty rows (common at the end of Excel sheets)
    while out and not any(out[-1]):
        out.pop()
    return Sheet(name=name, rows=out, truncated=truncated)


def read_table(file_type: str, data: bytes) -> list[Sheet]:
    if file_type == "csv":
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        return [_take(csv.reader(io.StringIO(text)), "Sheet 1")]

    if file_type == "xlsx":
        try:
            workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception as exc:  # openpyxl raises many types for broken files
            raise TableError("This spreadsheet could not be opened.") from exc
        try:
            return [
                _take(sheet.iter_rows(values_only=True), sheet.title)
                for sheet in workbook.worksheets
            ]
        finally:
            workbook.close()

    raise TableError("Only XLSX and CSV files have a table view.")
