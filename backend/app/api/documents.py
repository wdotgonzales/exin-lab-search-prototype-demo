import logging
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import AdminUser, CurrentUser, DbSession, client_ip
from app.config import get_settings
from app.core import audit
from app.core.files import CONTENT_TYPES, FileRejected, check_file
from app.core.storage import Storage, get_storage, inline_disposition
from app.core.tables import TableError, read_table
from app.ingest.extract import ExtractionError, extract
from app.models import Chunk, Document, DocumentEntity, Entity, Job, Source, User
from app.models.source import UPLOAD_SOURCE_NAME
from app.schemas.documents import (
    DeleteRequest,
    DeleteResult,
    DocumentDetail,
    DocumentList,
    DocumentOut,
    DocumentTable,
    DocumentText,
    LabIdOut,
    TableSheet,
    TextSection,
    UploadAccepted,
    UploadRejected,
    UploadResult,
    UploadSkipped,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

StorageDep = Annotated[Storage, Depends(get_storage)]

# The filename is the last part of external_path: uploads/{id}/{filename}
FILENAME = func.regexp_replace(Document.external_path, r"^.*/", "")


def _filename(doc: Document) -> str:
    return doc.external_path.rsplit("/", 1)[-1]


def _out(doc: Document, uploader: str | None) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        title=doc.title,
        filename=_filename(doc),
        file_type=doc.file_type,
        size_bytes=doc.size_bytes,
        status=doc.status,
        error_message=doc.error_message,
        uploaded_by_name=uploader,
        created_at=doc.created_at,
    )


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _get_or_404(db: DbSession, document_id: uuid.UUID) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return doc


@router.get("")
def list_documents(
    db: DbSession,
    user: CurrentUser,
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentList:
    stmt = select(Document, User.full_name).outerjoin(
        User, Document.uploaded_by == User.id
    )
    count = select(func.count()).select_from(Document)
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        match = or_(
            Document.title.ilike(pattern, escape="\\"),
            FILENAME.ilike(pattern, escape="\\"),
        )
        stmt = stmt.where(match)
        count = count.where(match)

    rows = db.execute(
        stmt.order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return DocumentList(
        items=[_out(doc, name) for doc, name in rows], total=db.scalar(count) or 0
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def upload_documents(
    user: CurrentUser,
    request: Request,
    db: DbSession,
    storage: StorageDep,
    files: Annotated[list[UploadFile], File()],
) -> UploadResult:
    settings = get_settings()
    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Upload at most {settings.max_files_per_upload} files at a time.",
        )

    source = db.scalar(
        select(Source).where(Source.kind == "upload", Source.name == UPLOAD_SOURCE_NAME)
    )
    if source is None:
        raise RuntimeError("The 'Manual uploads' source is missing; run migrations.")

    max_bytes = settings.max_file_mb * 1024 * 1024
    ip = client_ip(request)
    result = UploadResult()
    seen: set[str] = set()

    for upload in files:
        name = upload.filename or "file"
        data = upload.file.read(max_bytes + 1)  # never more than the limit + 1
        try:
            checked = check_file(name, data, max_bytes)
        except FileRejected as exc:
            result.rejected.append(UploadRejected(filename=name, reason=exc.reason))
            continue

        if checked.sha256 in seen:
            result.skipped.append(
                UploadSkipped(filename=name, reason="Same file twice in this upload.")
            )
            continue
        seen.add(checked.sha256)

        existing = db.scalar(
            select(Document).where(
                Document.source_id == source.id,
                Document.content_hash == checked.sha256,
            )
        )
        if existing is not None:
            result.skipped.append(
                UploadSkipped(
                    filename=name,
                    reason=f'Already uploaded as "{existing.title}".',
                    document_id=existing.id,
                )
            )
            continue

        document_id = uuid.uuid4()
        key = f"uploads/{document_id}/{checked.filename}"
        storage.put(key, data, checked.content_type)
        try:
            db.add(
                Document(
                    id=document_id,
                    source_id=source.id,
                    external_path=key,
                    title=checked.title,
                    file_type=checked.file_type,
                    size_bytes=checked.size_bytes,
                    content_hash=checked.sha256,
                    uploaded_by=user.id,
                )
            )
            db.add(
                Job(
                    job_type="ingest_document",
                    payload={"document_id": str(document_id)},
                )
            )
            audit.record(
                db,
                "document.upload",
                actor_user_id=user.id,
                actor_email=user.email,
                target_type="document",
                target_id=str(document_id),
                target_label=checked.filename,
                metadata={
                    "size_bytes": checked.size_bytes,
                    "content_hash": checked.sha256,
                },
                ip_address=ip,
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            storage.delete(key)  # don't leave an orphan file behind
            raise

        result.accepted.append(
            UploadAccepted(filename=checked.filename, document_id=document_id)
        )

    return result


@router.get("/{document_id}")
def get_document(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser
) -> DocumentDetail:
    doc = _get_or_404(db, document_id)
    uploader = db.get(User, doc.uploaded_by) if doc.uploaded_by else None
    passages = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == doc.id)
    )
    lab_ids = db.execute(
        select(Entity.code, Entity.entity_type, DocumentEntity.mention_count)
        .join(DocumentEntity, DocumentEntity.entity_id == Entity.id)
        .where(DocumentEntity.document_id == doc.id)
        .order_by(DocumentEntity.mention_count.desc(), Entity.code)
    ).all()
    base = _out(doc, uploader.full_name if uploader else None)
    return DocumentDetail(
        **base.model_dump(),
        summary=doc.summary,
        indexed_at=doc.indexed_at,
        passage_count=passages or 0,
        lab_ids=[
            LabIdOut(code=code, entity_type=kind, mentions=count)
            for code, kind, count in lab_ids
        ],
    )


@router.get("/{document_id}/file", response_model=None)
def open_file(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser, storage: StorageDep
) -> Response:
    doc = _get_or_404(db, document_id)
    filename = _filename(doc)
    url = storage.presigned_url(doc.external_path, filename)
    if url:
        return RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    return Response(
        content=storage.read(doc.external_path),
        media_type=CONTENT_TYPES[doc.file_type],
        headers={"Content-Disposition": inline_disposition(filename)},
    )


@router.post("/delete")
def delete_documents(
    admin: AdminUser,
    body: DeleteRequest,
    request: Request,
    db: DbSession,
    storage: StorageDep,
) -> DeleteResult:
    """Hard delete: rows (chunks and lab-ID links cascade), audit rows, then files."""
    ids = list(dict.fromkeys(body.document_ids))  # drop duplicates, keep order
    docs = db.scalars(select(Document).where(Document.id.in_(ids))).all()
    found = {doc.id for doc in docs}
    ip = client_ip(request)

    for doc in docs:
        audit.record(
            db,
            "document.delete",
            actor_user_id=admin.id,
            actor_email=admin.email,
            target_type="document",
            target_id=str(doc.id),
            target_label=doc.external_path.rsplit("/", 1)[-1],
            metadata={
                "title": doc.title,
                "file_type": doc.file_type,
                "size_bytes": doc.size_bytes,
                "content_hash": doc.content_hash,
                "uploaded_by": str(doc.uploaded_by) if doc.uploaded_by else None,
                "storage_key": doc.external_path,
            },
            ip_address=ip,
        )
    keys = [doc.external_path for doc in docs]
    if found:
        db.execute(delete(Document).where(Document.id.in_(found)))
    db.commit()

    # After the commit: a storage failure leaves an orphan file, never a broken row.
    for key in keys:
        try:
            storage.delete(key)
        except Exception:
            log.exception("could not delete %s from storage", key)

    return DeleteResult(
        deleted=[i for i in ids if i in found],
        not_found=[i for i in ids if i not in found],
    )


TEXT_PREVIEW_CHARS = 200_000


@router.get("/{document_id}/text")
def get_document_text(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser, storage: StorageDep
) -> DocumentText:
    """The text the indexer sees, per page or sheet, for the Extracted text tab."""
    doc = _get_or_404(db, document_id)
    try:
        sections = extract(doc.file_type, storage.read(doc.external_path))
    except ExtractionError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Couldn't read this file's text: {exc}",
        ) from exc

    out: list[TextSection] = []
    used = 0
    truncated = False
    for section in sections:
        room = TEXT_PREVIEW_CHARS - used
        if room <= 0:
            truncated = True
            break
        text = section.text[:room]
        truncated = truncated or len(text) < len(section.text)
        used += len(text)
        out.append(TextSection(label=section.label, page=section.page, text=text))
    return DocumentText(sections=out, truncated=truncated)


@router.get("/{document_id}/content", response_model=None)
def get_document_content(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser, storage: StorageDep
) -> Response:
    """The file itself from our own origin, for in-app viewers (no S3 CORS needed)."""
    doc = _get_or_404(db, document_id)
    return Response(
        content=storage.read(doc.external_path),
        media_type=CONTENT_TYPES[doc.file_type],
        headers={
            "Content-Disposition": inline_disposition(_filename(doc)),
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get("/{document_id}/table")
def get_document_table(
    document_id: uuid.UUID, db: DbSession, user: CurrentUser, storage: StorageDep
) -> DocumentTable:
    """XLSX or CSV as rows of text, for the table view."""
    doc = _get_or_404(db, document_id)
    if doc.file_type not in ("xlsx", "csv"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Only XLSX and CSV files have a table view."
        )
    try:
        sheets = read_table(doc.file_type, storage.read(doc.external_path))
    except TableError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return DocumentTable(
        sheets=[
            TableSheet(name=s.name, rows=s.rows, truncated=s.truncated) for s in sheets
        ]
    )
