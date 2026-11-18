import io
from datetime import date

import pytest
from docx import Document as DocxDocument
from openpyxl import Workbook

from app.ingest.extract import ExtractionError, Section, clean, extract


def make_pdf(pages: list[str]) -> bytes:
    """Build a tiny valid PDF with one line of Helvetica text per page."""
    objects: list[bytes] = []
    kids = " ".join(f"{4 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, text in enumerate(pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + i * 2} 0 R >>".encode()
        )
        objects.append(
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)
        )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (number, body))
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for offset in offsets:
        out.write(b"%010d 00000 n \n" % offset)
    out.write(
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
        % (len(objects) + 1, xref)
    )
    return out.getvalue()


def make_docx() -> bytes:
    doc = DocxDocument()
    doc.add_paragraph("Protocol for EXP-007")
    doc.add_paragraph("   ")  # blank paragraphs are skipped
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Mouse"
    table.rows[0].cells[1].text = "Weight"
    table.rows[1].cells[0].text = "M-042"
    table.rows[1].cells[1].text = "21 g"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Weights"
    ws.append(["Mouse", "Weight", "Date"])
    ws.append(["M-042", 21.0, date(2026, 3, 1)])
    ws.append([None, None, None])  # empty rows are skipped
    ws.append(["M-043", 19.5, None])
    empty = wb.create_sheet("Notes")  # sheet with nothing in it
    assert empty.max_row == 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_pdf_keeps_page_numbers():
    sections = extract("pdf", make_pdf(["Hello page one", "Results for M-042"]))
    assert [s.page for s in sections] == [1, 2]
    assert "Hello page one" in sections[0].text
    assert "M-042" in sections[1].text


def test_pdf_without_text_says_scanned():
    with pytest.raises(ExtractionError, match="scanned PDF"):
        extract("pdf", make_pdf([""]))


def test_broken_pdf_gives_friendly_error():
    with pytest.raises(ExtractionError, match="Could not read this PDF"):
        extract("pdf", b"%PDF-1.4 this is not really a pdf")


def test_docx_paragraphs_and_tables():
    [section] = extract("docx", make_docx())
    assert section.text == "Protocol for EXP-007\n\nMouse: M-042, Weight: 21 g"


def test_xlsx_rows_become_labelled_lines():
    sections = extract("xlsx", make_xlsx())
    assert sections == [
        Section(
            "Mouse: M-042, Weight: 21, Date: 2026-03-01\nMouse: M-043, Weight: 19.5",
            label="Sheet: Weights",
        )
    ]  # the empty "Notes" sheet is dropped


def test_csv_with_bom_and_semicolons():
    data = "\ufeffMouse;Virus\nM-042;V-003\n".encode()
    [section] = extract("csv", data)
    assert section.text == "Mouse: M-042, Virus: V-003"


def test_plain_text_is_cleaned():
    [section] = extract("txt", b"line one   \r\n\r\n\r\n\r\nline two\x00\n")
    assert section.text == "line one\n\nline two"


def test_empty_text_file_is_rejected():
    with pytest.raises(ExtractionError, match="No readable text"):
        extract("md", b"   \n\n")


def test_unknown_type_is_rejected():
    with pytest.raises(ExtractionError, match="Unsupported"):
        extract("exe", b"MZ")


def test_clean_collapses_blank_lines():
    assert clean("a\n\n\n\nb  \n") == "a\n\nb"
