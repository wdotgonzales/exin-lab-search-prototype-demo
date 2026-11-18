"""Read-only tools the chat agent can call, plus the catalogue it always sees.

Every tool:
- only reads (no tool can change, delete or create anything),
- applies the same access rule as the rest of the app (viewers only see
  access_level 'general'),
- returns compact JSON, numbering each document it mentions as a source [n].

The numbering lives in `Sources`, shared by all tools in one request, so a
document has the same number whichever tool found it, and the answer's [n]
citations can be turned into source cards afterwards.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.chat.retrieval import retrieve
from app.ingest.embedder import Embedder
from app.ingest.lab_ids import find_lab_ids
from app.models import Chunk, Document, DocumentEntity, Entity, User

CATALOGUE_LIMIT = 150  # newest documents listed in every request
LIST_LIMIT = 50
READ_MAX_CHARS = 40_000  # about 10,000 tokens of one document
FILE_TYPES = ("pdf", "docx", "xlsx", "csv", "md", "txt")
STATUSES = ("pending", "processing", "indexed", "failed")


# ── the shared source numbering ─────────────────────────────────


@dataclass
class SourceDoc:
    n: int
    document_id: uuid.UUID
    title: str
    filename: str
    summary: str | None
    passage: str | None = None  # best passage a tool returned, for the card
    page: int | None = None


@dataclass
class Sources:
    docs: dict[uuid.UUID, SourceDoc] = field(default_factory=dict)
    chunk_ids: list[int] = field(default_factory=list)

    def add(self, doc: Document) -> int:
        if doc.id not in self.docs:
            filename = doc.external_path.rsplit("/", 1)[-1]
            self.docs[doc.id] = SourceDoc(
                len(self.docs) + 1, doc.id, doc.title, filename, doc.summary
            )
        return self.docs[doc.id].n

    def note_passage(self, document_id: uuid.UUID, text: str, page: int | None) -> None:
        source = self.docs.get(document_id)
        if source is not None and source.passage is None:
            source.passage, source.page = text, page

    def by_number(self, n: int) -> SourceDoc | None:
        return next((s for s in self.docs.values() if s.n == n), None)


@dataclass
class ToolContext:
    db: Session
    embedder: Embedder
    is_admin: bool
    sources: Sources = field(default_factory=Sources)


class ToolError(Exception):
    """A problem the model can fix, e.g. a bad date. Sent back to it as text."""


def _visible(ctx: ToolContext) -> list[ColumnElement[bool]]:
    return [] if ctx.is_admin else [Document.access_level == "general"]


def _doc_row(ctx: ToolContext, doc: Document, uploader: str | None) -> dict[str, Any]:
    return {
        "source": ctx.sources.add(doc),
        "title": doc.title,
        "file": doc.external_path.rsplit("/", 1)[-1],
        "type": doc.file_type,
        "uploaded": doc.created_at.date().isoformat(),
        "uploaded_by": uploader or "unknown",
        "status": doc.status,
        "summary": doc.summary,
    }


# ── the catalogue (in every request) ────────────────────────────


def catalogue(ctx: ToolContext) -> str:
    """One line per document, newest first, so the agent always knows what exists."""
    total = ctx.db.scalar(
        select(func.count()).select_from(Document).where(*_visible(ctx))
    )
    rows = ctx.db.execute(
        select(Document, User.full_name)
        .outerjoin(User, User.id == Document.uploaded_by)
        .where(*_visible(ctx))
        .order_by(Document.created_at.desc(), Document.id)
        .limit(CATALOGUE_LIMIT)
    ).all()
    lines = []
    for doc, uploader in rows:
        d = _doc_row(ctx, doc, uploader)
        summary = f" Summary: {d['summary']}" if d["summary"] else ""
        lines.append(
            f"[{d['source']}] {d['title']} | {d['file']} | {d['type']} | "
            f"uploaded {d['uploaded']} by {d['uploaded_by']} | {d['status']}.{summary}"
        )
    more = total - len(rows) if total else 0
    if more > 0:
        lines.append(f"(+{more} older documents: use list_documents to see them)")
    return "\n".join(lines) or "(no documents uploaded yet)"


# ── the tools ───────────────────────────────────────────────────


def search_passages(ctx: ToolContext, query: str) -> dict[str, Any]:
    result = retrieve(ctx.db, query, ctx.embedder, is_admin=ctx.is_admin)
    if not result.found:
        return {"results": [], "note": "No relevant passages found."}
    grouped: dict[uuid.UUID, dict[str, Any]] = {}
    docs = {
        d.id: d
        for d in ctx.db.scalars(
            select(Document).where(
                Document.id.in_({c.document_id for c in result.chunks})
            )
        )
    }
    for chunk in result.chunks:
        ctx.sources.chunk_ids.append(chunk.chunk_id)
        doc = docs[chunk.document_id]
        n = ctx.sources.add(doc)
        ctx.sources.note_passage(doc.id, chunk.content, chunk.page_number)
        entry = grouped.setdefault(
            doc.id,
            {"source": n, "title": doc.title, "file": chunk.filename, "passages": []},
        )
        entry["passages"].append({"page": chunk.page_number, "text": chunk.content})
    return {"results": list(grouped.values())}


def list_documents(
    ctx: ToolContext,
    title_contains: str | None = None,
    file_type: str | None = None,
    uploaded_after: str | None = None,
    uploaded_before: str | None = None,
    mentions: str | None = None,
    uploaded_by: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    stmt = (
        select(Document, User.full_name)
        .outerjoin(User, User.id == Document.uploaded_by)
        .where(*_visible(ctx))
    )
    if title_contains:
        pattern = f"%{_escape(title_contains)}%"
        stmt = stmt.where(
            or_(
                Document.title.ilike(pattern, escape="\\"),
                Document.external_path.ilike(pattern, escape="\\"),
            )
        )
    if file_type:
        if file_type.lower() not in FILE_TYPES:
            raise ToolError(f"file_type must be one of {', '.join(FILE_TYPES)}")
        stmt = stmt.where(Document.file_type == file_type.lower())
    if uploaded_after:
        stmt = stmt.where(Document.created_at >= _date(uploaded_after))
    if uploaded_before:  # inclusive: the whole "before" day counts
        stmt = stmt.where(
            Document.created_at < _date(uploaded_before) + timedelta(days=1)
        )
    if mentions:
        code = _lab_id(mentions)
        stmt = stmt.where(
            Document.id.in_(
                select(DocumentEntity.document_id)
                .join(Entity, Entity.id == DocumentEntity.entity_id)
                .where(Entity.code == code)
            )
        )
    if uploaded_by:
        stmt = stmt.where(
            User.full_name.ilike(f"%{_escape(uploaded_by)}%", escape="\\")
        )
    if status:
        if status not in STATUSES:
            raise ToolError(f"status must be one of {', '.join(STATUSES)}")
        stmt = stmt.where(Document.status == status)

    total = ctx.db.scalar(select(func.count()).select_from(stmt.subquery()))
    size = max(1, min(limit or 20, LIST_LIMIT))
    rows = ctx.db.execute(
        stmt.order_by(Document.created_at.desc(), Document.id).limit(size)
    ).all()
    return {"total": total, "documents": [_doc_row(ctx, d, u) for d, u in rows]}


def read_document(ctx: ToolContext, source: int) -> dict[str, Any]:
    known = ctx.sources.by_number(source)
    if known is None:
        raise ToolError(
            f"No source [{source}]. Use the catalogue numbers or another tool first."
        )
    doc = ctx.db.scalar(
        select(Document).where(Document.id == known.document_id, *_visible(ctx))
    )
    if doc is None:
        raise ToolError(f"Source [{source}] is not available.")
    if doc.status != "indexed":
        return {
            "source": source,
            "title": doc.title,
            "note": f"Not readable yet: {doc.status}.",
        }

    parts, size, truncated = [], 0, False
    for chunk in ctx.db.scalars(
        select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.chunk_index)
    ):
        if size + len(chunk.content) > READ_MAX_CHARS:
            truncated = True
            break
        ctx.sources.chunk_ids.append(chunk.id)
        ctx.sources.note_passage(doc.id, chunk.content, chunk.page_number)
        page = f"(page {chunk.page_number})\n" if chunk.page_number else ""
        parts.append(page + chunk.content)
        size += len(chunk.content)
    return {
        "source": source,
        "title": doc.title,
        "text": "\n---\n".join(parts),
        "truncated": truncated,
    }


def lab_id_info(ctx: ToolContext, code: str) -> dict[str, Any]:
    canonical = _lab_id(code)
    rows = ctx.db.execute(
        select(Document, DocumentEntity.mention_count, Entity.entity_type)
        .join(DocumentEntity, DocumentEntity.document_id == Document.id)
        .join(Entity, Entity.id == DocumentEntity.entity_id)
        .where(Entity.code == canonical, *_visible(ctx))
        .order_by(DocumentEntity.mention_count.desc(), Document.created_at.desc())
    ).all()
    return {
        "code": canonical,
        "type": rows[0][2] if rows else None,
        "documents": [
            {"source": ctx.sources.add(doc), "title": doc.title, "mentions": count}
            for doc, count, _ in rows
        ],
    }


def collection_stats(ctx: ToolContext) -> dict[str, Any]:
    vis = _visible(ctx)

    def grouped(column: Any) -> dict[str, int]:
        rows = ctx.db.execute(
            select(column, func.count())
            .select_from(Document)
            .outerjoin(User, User.id == Document.uploaded_by)
            .where(*vis)
            .group_by(column)
            .order_by(func.count().desc())
        ).all()
        return {str(key or "unknown"): count for key, count in rows}

    total, latest = ctx.db.execute(
        select(func.count(), func.max(Document.created_at))
        .select_from(Document)
        .where(*vis)
    ).one()
    return {
        "total": total,
        "latest_upload": latest.date().isoformat() if latest else None,
        "by_status": grouped(Document.status),
        "by_type": grouped(Document.file_type),
        "by_uploader": grouped(User.full_name),
    }


# ── registry: what the model sees, and how calls are run ────────


def _nullable(kind: str, description: str, **extra: Any) -> dict[str, Any]:
    return {"type": [kind, "null"], "description": description, **extra}


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_passages",
        "description": "Search inside the documents' text, by keywords, lab IDs and meaning. "
        "Use for questions about what documents say.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for."}
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_documents",
        "description": "List documents by their details (not their text): title or file "
        "name, type, upload dates, a lab ID they mention, uploader, status. Returns each "
        "document's summary. Newest first.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "title_contains": _nullable(
                    "string", "Part of the title or file name."
                ),
                "file_type": _nullable("string", "One of: " + ", ".join(FILE_TYPES)),
                "uploaded_after": _nullable("string", "YYYY-MM-DD, inclusive."),
                "uploaded_before": _nullable("string", "YYYY-MM-DD, inclusive."),
                "mentions": _nullable("string", "A lab ID such as M-042 or EXP-007."),
                "uploaded_by": _nullable("string", "Part of the uploader's name."),
                "status": _nullable("string", "One of: " + ", ".join(STATUSES)),
                "limit": _nullable(
                    "integer", f"How many to return, at most {LIST_LIMIT}."
                ),
            },
            "required": [
                "title_contains",
                "file_type",
                "uploaded_after",
                "uploaded_before",
                "mentions",
                "uploaded_by",
                "status",
                "limit",
            ],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_document",
        "description": "Read the full text of one document, by its source number. "
        "Use to summarize or answer detailed questions about a specific document.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "integer", "description": "Its [n] number."}
            },
            "required": ["source"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "lab_id_info",
        "description": "Which documents mention a lab ID (mouse M-###, virus V-###, "
        "experiment EXP-###, cohort C-##) and how often.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "e.g. C-07"}},
            "required": ["code"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "collection_stats",
        "description": "Counts of documents by status, file type and uploader, the total, "
        "and the latest upload date.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    },
]

_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "search_passages": search_passages,
    "list_documents": list_documents,
    "read_document": read_document,
    "lab_id_info": lab_id_info,
    "collection_stats": collection_stats,
}


def run_tool(ctx: ToolContext, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run one tool call from the model. Mistakes come back as {"error": ...}
    so the model can correct itself; real failures (database down) still raise."""
    runner = _RUNNERS.get(name)
    if runner is None:
        return {"error": f"Unknown tool {name!r}."}
    try:
        return runner(ctx, **{k: v for k, v in args.items() if v is not None})
    except (ToolError, TypeError) as exc:
        return {"error": str(exc)}


def result_count(result: dict[str, Any]) -> int:
    """How many things a tool returned, for the ai_queries log."""
    for key in ("results", "documents"):
        if isinstance(result.get(key), list):
            return len(result[key])
    return 0 if "error" in result else 1


# ── helpers ─────────────────────────────────────────────────────


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ToolError(f"Dates must look like 2026-11-19, not {value!r}.") from None


def _lab_id(value: str) -> str:
    found = list(find_lab_ids(value))
    if not found:
        raise ToolError(
            f"{value!r} is not a lab ID like M-042, V-019, EXP-007 or C-07."
        )
    return found[0].code
