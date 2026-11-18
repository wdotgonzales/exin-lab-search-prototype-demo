import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    file_type: str
    size_bytes: int | None
    status: str
    error_message: str | None
    uploaded_by_name: str | None
    created_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentOut]
    total: int


class UploadAccepted(BaseModel):
    filename: str
    document_id: uuid.UUID


class UploadSkipped(BaseModel):
    filename: str
    reason: str
    document_id: uuid.UUID | None = None


class UploadRejected(BaseModel):
    filename: str
    reason: str


class UploadResult(BaseModel):
    accepted: list[UploadAccepted] = []
    skipped: list[UploadSkipped] = []
    rejected: list[UploadRejected] = []
