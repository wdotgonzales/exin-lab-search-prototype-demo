import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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


class DeleteRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class DeleteResult(BaseModel):
    deleted: list[uuid.UUID]
    not_found: list[uuid.UUID]


class LabIdOut(BaseModel):
    code: str
    entity_type: str
    mentions: int


class DocumentDetail(DocumentOut):
    summary: str | None
    indexed_at: datetime | None
    passage_count: int
    lab_ids: list[LabIdOut]


class TextSection(BaseModel):
    label: str | None
    page: int | None
    text: str


class DocumentText(BaseModel):
    sections: list[TextSection]
    truncated: bool
