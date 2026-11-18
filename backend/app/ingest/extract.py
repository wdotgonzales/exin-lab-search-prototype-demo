"""Turn an uploaded file's bytes into plain text sections.

Each Section is one piece of the document in reading order: a PDF page, a
spreadsheet sheet, or the whole text of a DOCX/MD/TXT file. The chunker cuts
sections into ~500-token chunks; a section's page number travels with its
chunks so chat answers can cite "page 3".
"""

import csv
import io
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from docx import Document as DocxDocument
from openpyxl import load_workbook
from pypdf import PdfReader

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Section:
    text: str
    page: int | None = None  # PDF page number, 1-based
    label: str | None = None  # e.g. "Sheet: Weights"; repeated at the top of each chunk


class ExtractionError(Exception):
    """Raised with a message that is safe to show to users."""


def extract(file_type: str, data: bytes) -> list[Section]:
    readers = {
        "pdf": _pdf,
        "docx": _docx,
        "xlsx": _xlsx,
        "csv": _csv,
        "md": _plain,
        "txt": _plain,
    }
    reader = readers.get(file_type)
    if reader is None:
        raise ExtractionError(f"Unsupported file type: {file_type}")

    try:
        sections = reader(data)
    except ExtractionError:
        raise
    except Exception as exc:  # third-party parsers raise many different errors
        log.warning("extract failed for %s file: %r", file_type, exc)
        raise ExtractionError(
            f"Could not read this {file_type.upper()} file. It may be damaged."
        ) from exc

    sections = [s for s in sections if s.text]
    if not sections:
        if file_type == "pdf":
            raise ExtractionError("No text found. Is it a scanned PDF?")
        raise ExtractionError("No readable text found in this file.")
    return sections


# ── cleaning helpers ────────────────────────────────────────────


def clean(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)  # trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)  # at most one blank line
    return text.strip()


def _fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return (
            value.date().isoformat()
            if value.time() == datetime.min.time()
            else value.isoformat(" ")
        )
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _table_lines(rows: Iterable[Iterable[object]]) -> list[str]:
    """First non-empty row is the header; every other row becomes
    'Column: value, Column: value' so each line makes sense on its own."""
    header: list[str] | None = None
    lines: list[str] = []
    for raw in rows:
        cells = [_fmt(v) for v in raw]
        if not any(cells):
            continue
        if header is None:
            header = [c or f"Column {i}" for i, c in enumerate(cells, 1)]
            continue
        pairs = [
            f"{header[i] if i < len(header) else f'Column {i + 1}'}: {c}"
            for i, c in enumerate(cells)
            if c
        ]
        lines.append(", ".join(pairs))
    if header is not None and not lines:  # header-only table: keep the header text
        lines.append(", ".join(header))
    return lines


# ── one reader per file type ────────────────────────────────────


def _pdf(data: bytes) -> list[Section]:
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ExtractionError("This PDF is password-protected.")
    return [
        Section(clean(page.extract_text() or ""), page=number)
        for number, page in enumerate(reader.pages, 1)
    ]


def _docx(data: bytes) -> list[Section]:
    doc = DocxDocument(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        rows = ([cell.text for cell in row.cells] for row in table.rows)
        parts.extend(_table_lines(rows))
    return [Section(clean("\n\n".join(parts)))]


def _xlsx(data: bytes) -> list[Section]:
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        return [
            Section(
                clean("\n".join(_table_lines(ws.iter_rows(values_only=True)))),
                label=f"Sheet: {ws.title}",
            )
            for ws in wb.worksheets
        ]
    finally:
        wb.close()


def _csv(data: bytes) -> list[Section]:
    text = data.decode("utf-8-sig")
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(
            text[:4096], delimiters=",;\t"
        )
    except csv.Error:
        dialect = csv.excel
    rows = csv.reader(io.StringIO(text), dialect)
    return [Section(clean("\n".join(_table_lines(rows))))]


def _plain(data: bytes) -> list[Section]:
    return [Section(clean(data.decode("utf-8-sig")))]
