import hashlib
import io
import zipfile

import pytest

from app.core.files import FileRejected, check_file, safe_filename, title_from

MB = 1024 * 1024
PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def office_zip(member: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, "<xml/>")
    return buf.getvalue()


def test_valid_pdf_is_described():
    checked = check_file("EXP-007_imaging_notebook.pdf", PDF, 25 * MB)
    assert checked.filename == "EXP-007_imaging_notebook.pdf"
    assert checked.title == "EXP-007 imaging notebook"
    assert checked.file_type == "pdf"
    assert checked.content_type == "application/pdf"
    assert checked.size_bytes == len(PDF)
    assert checked.sha256 == hashlib.sha256(PDF).hexdigest()


@pytest.mark.parametrize(
    ("name", "data", "file_type"),
    [
        ("notes.docx", office_zip("word/document.xml"), "docx"),
        ("colony.xlsx", office_zip("xl/workbook.xml"), "xlsx"),
        ("log.csv", b"mouse,date\nM-042,2026-09-09\n", "csv"),
        ("README.md", "# Notes \u2014 \u00b5L\n".encode(), "md"),
        ("bom.txt", b"\xef\xbb\xbfhello", "txt"),
        ("UPPER.PDF", PDF, "pdf"),
    ],
)
def test_supported_types_pass(name, data, file_type):
    assert check_file(name, data, 25 * MB).file_type == file_type


@pytest.mark.parametrize(
    ("name", "data", "reason"),
    [
        ("cage_photo.png", PNG, "PNG isn't supported"),
        ("no_extension", PDF, "without an extension"),
        ("renamed.pdf", PNG, "isn't a real PDF"),
        ("fake.docx", office_zip("other.xml"), "isn't a real Word"),
        ("fake.xlsx", PDF, "isn't a real Excel"),
        ("binary.txt", PNG, "isn't plain text"),
        ("latin1.csv", "caf\u00e9".encode("latin-1"), "isn't plain text"),
        ("empty.pdf", b"", "The file is empty"),
    ],
)
def test_bad_files_are_rejected_with_a_reason(name, data, reason):
    with pytest.raises(FileRejected) as exc:
        check_file(name, data, 25 * MB)
    assert reason in exc.value.reason


def test_too_large_is_rejected():
    with pytest.raises(FileRejected) as exc:
        check_file("big.pdf", PDF + b"x" * MB, MB)
    assert exc.value.reason == "Larger than 1 MB."


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("../../etc/passwd.txt", "passwd.txt"),
        ("C:\\Users\\wilson\\My Notes.md", "My Notes.md"),
        ("weird<>:|?*name.csv", "weird_name.csv"),
        ("...", "file"),
    ],
)
def test_safe_filename(raw, clean):
    assert safe_filename(raw) == clean


def test_title_from():
    assert title_from("C-07_surgery_log.csv") == "C-07 surgery log"
    assert title_from("report.pdf") == "report"
