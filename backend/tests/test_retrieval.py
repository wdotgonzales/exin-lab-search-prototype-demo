import uuid

import pytest
from sqlalchemy import select

from app.chat.retrieval import retrieve, rrf
from app.ingest.embedder import FakeEmbedder
from app.models import Chunk, Document, DocumentEntity, Entity, Source
from app.models.source import UPLOAD_SOURCE_NAME

EMBEDDER = FakeEmbedder()


def add_document(
    db,
    title: str,
    texts: list[str],
    *,
    status: str = "indexed",
    access_level: str = "general",
    lab_ids: tuple[tuple[str, str], ...] = (),
) -> Document:
    """A document as the worker leaves it: chunks with vectors, lab IDs linked."""
    source = db.scalar(select(Source).where(Source.name == UPLOAD_SOURCE_NAME))
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        source_id=source.id,
        external_path=f"uploads/{doc_id}/{title}.txt",
        title=title,
        file_type="txt",
        size_bytes=1,
        content_hash="0" * 64,
        status=status,
        access_level=access_level,
    )
    db.add(doc)
    db.flush()
    db.add_all(
        Chunk(
            document_id=doc_id,
            chunk_index=i,
            content=text,
            token_count=1,
            embedding=vector,
            embedding_model=EMBEDDER.model,
        )
        for i, (text, vector) in enumerate(
            zip(texts, EMBEDDER.embed(texts), strict=True)
        )
    )
    for code, entity_type in lab_ids:
        entity = Entity(code=code, entity_type=entity_type)
        db.add(entity)
        db.flush()
        db.add(DocumentEntity(document_id=doc_id, entity_id=entity.id, mention_count=1))
    db.commit()
    return doc


def titles(result) -> list[str]:
    return [chunk.title for chunk in result.chunks]


def test_rrf_rewards_chunks_found_by_several_searches():
    ranked = rrf([[1, 2, 3], [3, 4], [3]])
    assert [chunk_id for chunk_id, _ in ranked] == [3, 1, 2, 4]


def test_meaning_search_finds_the_closest_text(db_session):
    add_document(db_session, "window incident", ["The cranial window cracked."])
    add_document(db_session, "weights", ["Weights were recorded on Monday."])

    # The fake embedder gives identical text an identical vector: similarity 1.0.
    result = retrieve(
        db_session, "The cranial window cracked.", EMBEDDER, is_admin=True
    )

    assert titles(result)[0] == "window incident"
    assert result.best_similarity == pytest.approx(1.0)
    assert result.found


def test_keyword_search_matches_any_word(db_session):
    add_document(db_session, "window incident", ["The cranial window cracked."])
    add_document(db_session, "weights", ["Weights were recorded on Monday."])

    result = retrieve(
        db_session, "which mouse had a broken window yesterday", EMBEDDER, is_admin=True
    )

    assert result.keyword_hits == 1  # only "window" matches, and that is enough
    assert titles(result)[0] == "window incident"
    assert result.found


def test_lab_id_finds_documents_that_mention_it(db_session):
    add_document(
        db_session,
        "surgery notes",
        ["Notes for m-42 surgery."],
        lab_ids=(("M-042", "mouse"),),
    )
    add_document(db_session, "weights", ["Weights were recorded on Monday."])

    result = retrieve(db_session, "What happened to M-042?", EMBEDDER, is_admin=True)

    assert result.id_hits == 1
    assert titles(result)[0] == "surgery notes"


def test_unrelated_question_is_not_found(db_session):
    add_document(db_session, "window incident", ["The cranial window cracked."])

    result = retrieve(db_session, "zebra quantum pizza", EMBEDDER, is_admin=True)

    assert (result.id_hits, result.keyword_hits) == (0, 0)
    assert result.best_similarity < 0.30  # random fake vectors are far apart
    assert not result.found


def test_only_indexed_and_allowed_documents_are_searched(db_session):
    add_document(db_session, "pending", ["window"], status="pending")
    add_document(db_session, "secret", ["window"], access_level="restricted")
    add_document(db_session, "public", ["window"])

    as_viewer = retrieve(db_session, "window", EMBEDDER, is_admin=False)
    as_admin = retrieve(db_session, "window", EMBEDDER, is_admin=True)

    assert titles(as_viewer) == ["public"]
    assert sorted(titles(as_admin)) == ["public", "secret"]
