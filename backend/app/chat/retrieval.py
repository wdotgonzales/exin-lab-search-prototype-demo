"""Find the chunks that best answer a question (hybrid retrieval).

Three searches, merged with Reciprocal Rank Fusion (RRF):
- lab IDs in the question (M-042, EXP-007...) -> chunks of documents that mention them
- keyword search on chunks.search_vector: ANY word may match, more matches rank higher
- meaning search on chunks.embedding: cosine distance, served by the HNSW index

Only indexed documents are searched, and viewers only see access_level 'general'.
"""

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.ingest.embedder import Embedder
from app.ingest.lab_ids import find_lab_ids
from app.models import Chunk, Document, DocumentEntity, Entity

CANDIDATES = 50  # per search, before merging
TOP_K = 8  # chunks handed to the answer step
RRF_K = 60  # standard RRF constant: dampens the weight of the very top ranks
MIN_SIMILARITY = 0.30  # below this, meaning search alone doesn't count as "found"


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: uuid.UUID
    title: str
    external_path: str
    content: str
    page_number: int | None
    score: float

    @property
    def filename(self) -> str:
        return self.external_path.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Retrieval:
    chunks: list[RetrievedChunk]
    id_hits: int
    keyword_hits: int
    best_similarity: float | None

    @property
    def found(self) -> bool:
        """Worth asking the AI? An exact ID or keyword match, or a close meaning."""
        if not self.chunks:
            return False
        close = (self.best_similarity or 0.0) >= MIN_SIMILARITY
        return self.id_hits > 0 or self.keyword_hits > 0 or close


def retrieve(
    db: Session,
    question: str,
    embedder: Embedder,
    *,
    is_admin: bool,
    top_k: int = TOP_K,
) -> Retrieval:
    visible = _visible(is_admin)
    by_id = _lab_id_search(db, question, visible)
    by_keyword = _keyword_search(db, question, visible)
    by_meaning = _meaning_search(
        db, embedder.embed([question])[0], embedder.model, visible
    )

    ranked = rrf([by_id, by_keyword, [chunk_id for chunk_id, _ in by_meaning]])[:top_k]
    return Retrieval(
        chunks=_load(db, ranked),
        id_hits=len(by_id),
        keyword_hits=len(by_keyword),
        best_similarity=by_meaning[0][1] if by_meaning else None,
    )


def rrf(rankings: list[list[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion: each list adds 1 / (k + rank) to a chunk's score,
    so chunks found by several searches rise to the top."""
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, 1):
            scores[chunk_id] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


# ── the three searches ──────────────────────────────────────────


def _visible(is_admin: bool) -> list[ColumnElement[bool]]:
    conditions = [Document.status == "indexed"]
    if not is_admin:
        conditions.append(Document.access_level == "general")
    return conditions


def _lab_id_search(
    db: Session, question: str, visible: list[ColumnElement[bool]]
) -> list[int]:
    codes = [lab.code for lab in find_lab_ids(question)]
    if not codes:
        return []
    # Chunks that literally contain the ID first, then the rest of those documents.
    mentions = or_(*(Chunk.content.ilike(f"%{code}%") for code in codes))
    return list(
        db.scalars(
            select(Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
            .join(DocumentEntity, DocumentEntity.document_id == Chunk.document_id)
            .join(Entity, Entity.id == DocumentEntity.entity_id)
            .where(Entity.code.in_(codes), *visible)
            .group_by(Chunk.id)
            .order_by(
                func.bool_or(mentions).desc(),
                func.sum(DocumentEntity.mention_count).desc(),
                Chunk.id,
            )
            .limit(CANDIDATES)
        )
    )


def _keyword_search(
    db: Session, question: str, visible: list[ColumnElement[bool]]
) -> list[int]:
    # Letters and digits only, so the user can't inject tsquery syntax.
    words = sorted(
        {w.lower() for w in re.findall(r"[A-Za-z0-9]+", question) if len(w) > 1}
    )
    if not words:
        return []
    query = func.to_tsquery("english", " | ".join(words[:40]))  # OR: any word may match
    return list(
        db.scalars(
            select(Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.search_vector.op("@@")(query), *visible)
            .order_by(func.ts_rank(Chunk.search_vector, query).desc(), Chunk.id)
            .limit(CANDIDATES)
        )
    )


def _meaning_search(
    db: Session, vector: list[float], model: str, visible: list[ColumnElement[bool]]
) -> list[tuple[int, float]]:
    distance = Chunk.embedding.cosine_distance(vector)
    rows = db.execute(
        select(Chunk.id, distance)
        .join(Document, Document.id == Chunk.document_id)
        # never compare vectors made by different models
        .where(Chunk.embedding.is_not(None), Chunk.embedding_model == model, *visible)
        .order_by(distance)
        .limit(CANDIDATES)
    ).all()
    return [(chunk_id, 1 - d) for chunk_id, d in rows]


def _load(db: Session, ranked: list[tuple[int, float]]) -> list[RetrievedChunk]:
    if not ranked:
        return []
    rows = db.execute(
        select(
            Chunk.id,
            Chunk.document_id,
            Document.title,
            Document.external_path,
            Chunk.content,
            Chunk.page_number,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.id.in_([chunk_id for chunk_id, _ in ranked]))
    ).all()
    by_id = {row.id: row for row in rows}
    return [
        RetrievedChunk(
            chunk_id=row.id,
            document_id=row.document_id,
            title=row.title,
            external_path=row.external_path,
            content=row.content,
            page_number=row.page_number,
            score=score,
        )
        for chunk_id, score in ranked
        if (row := by_id.get(chunk_id)) is not None
    ]
