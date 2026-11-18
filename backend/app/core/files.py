"""Checks an uploaded file before it is stored: name, type, real content, size, hash."""

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import PurePath

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "md": "text/markdown",
    "txt": "text/plain",
}
ALLOWED_LIST = "PDF, DOCX, XLSX, CSV, MD or TXT"


class FileRejected(Exception):
    """The file can't be accepted; `reason` is shown to the user."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class CheckedFile:
    filename: str
    title: str
    file_type: str
    content_type: str
    size_bytes: int
    sha256: str


def safe_filename(name: str) -> str:
    """Keep only the last path part and safe characters."""
    name = PurePath(name.replace("\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name[:200] or "file"


def title_from(filename: str) -> str:
    """'EXP-007_imaging_notebook.pdf' -> 'EXP-007 imaging notebook'."""
    stem = PurePath(filename).stem
    return re.sub(r"_+", " ", stem).strip() or filename


def _zip_has(data: bytes, member: str) -> bool:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return member in zf.namelist()
    except zipfile.BadZipFile:
        return False


def _is_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return True


def _check_content(file_type: str, data: bytes) -> None:
    if file_type == "pdf" and not data.startswith(b"%PDF-"):
        raise FileRejected("This isn't a real PDF.")
    if file_type == "docx" and not _zip_has(data, "word/document.xml"):
        raise FileRejected("This isn't a real Word (.docx) document.")
    if file_type == "xlsx" and not _zip_has(data, "xl/workbook.xml"):
        raise FileRejected("This isn't a real Excel (.xlsx) workbook.")
    if file_type in ("csv", "md", "txt") and not _is_text(data):
        raise FileRejected("This file isn't plain text (UTF-8).")


def check_file(original_name: str, data: bytes, max_bytes: int) -> CheckedFile:
    filename = safe_filename(original_name)
    suffix = PurePath(filename).suffix.lower().lstrip(".")

    if suffix not in CONTENT_TYPES:
        shown = suffix.upper() if suffix else "Files without an extension"
        raise FileRejected(f"{shown} isn't supported. Use {ALLOWED_LIST}.")
    if not data:
        raise FileRejected("The file is empty.")
    if len(data) > max_bytes:
        raise FileRejected(f"Larger than {max_bytes // (1024 * 1024)} MB.")
    _check_content(suffix, data)

    return CheckedFile(
        filename=filename,
        title=title_from(filename),
        file_type=suffix,
        content_type=CONTENT_TYPES[suffix],
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
