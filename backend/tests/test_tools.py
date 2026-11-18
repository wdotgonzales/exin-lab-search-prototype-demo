import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.chat.tools import (
    ToolContext,
    catalogue,
    collection_stats,
    lab_id_info,
    list_documents,
    read_document,
    result_count,
    run_tool,
    search_passages,
)
from app.ingest.embedder import FakeEmbedder
from app.models import Chunk, Document, DocumentEntity, Entity, Source, User
from app.models.source import UPLOAD_SOURCE_NAME

EMBEDDER = FakeEmbedder()


@pytest.fixture
def lab(db_session):
    """Three documents by two people; one restricted, one still pending."""
    alice = User(
        email="alice@exin.test",
        password_hash="x",
        full_name="Alice Admin",
        role="admin",
    )
    bob = User(
        email="bob@exin.test",
        password_hash="x",
        full_name="Bob Biologist",
        role="viewer",
    )
    db_session.add_all([alice, bob])
    db_session.flush()
    source = db_session.scalar(select(Source).where(Source.name == UPLOAD_SOURCE_NAME))
    entity = Entity(code="M-045", entity_type="mouse")
    db_session.add(entity)
    db_session.flush()

    def add(
        title,
        ftype,
        day,
        uploader,
        texts,
        *,
        access="general",
        status="indexed",
        m045=0,
    ):
        doc_id = uuid.uuid4()
        db_session.add(
            Document(
                id=doc_id,
                source_id=source.id,
                external_path=f"uploads/{doc_id}/{title.replace(' ', '_')}.{ftype}",
                title=title,
                file_type=ftype,
                size_bytes=1,
                content_hash="0" * 64,
                status=status,
                access_level=access,
                uploaded_by=uploader.id,
                summary=f"Summary of {title}.",
                created_at=datetime(2026, 11, day, 9, tzinfo=UTC),
            )
        )
        db_session.flush()
        for i, (text, vector) in enumerate(
            zip(texts, EMBEDDER.embed(texts), strict=True)
        ):
            db_session.add(
                Chunk(
                    document_id=doc_id,
                    chunk_index=i,
                    content=text,
                    token_count=1,
                    page_number=i + 1 if ftype == "pdf" else None,
                    embedding=vector,
                    embedding_model=EMBEDDER.model,
                )
            )
        if m045:
            db_session.add(
                DocumentEntity(
                    document_id=doc_id, entity_id=entity.id, mention_count=m045
                )
            )
        return doc_id

    ids = {
        "incident": add(
            "incident M-045 window",
            "md",
            18,
            alice,
            ["The window on M-045 clouded."],
            m045=3,
        ),
        "report": add(
            "EXP-007 report",
            "pdf",
            17,
            bob,
            ["Page one.", "M-045 was excluded."],
            m045=1,
        ),
        "secret": add(
            "restricted plan",
            "docx",
            18,
            alice,
            ["window secrets"],
            access="restricted",
        ),
        "pending": add("new upload", "csv", 19, bob, [], status="pending"),
    }
    db_session.commit()
    return ids


def ctx(db, admin=True) -> ToolContext:
    return ToolContext(db=db, embedder=EMBEDDER, is_admin=admin)


def titles(result) -> list[str]:
    return [d["title"] for d in result["documents"]]


def test_catalogue_lists_every_visible_document_with_numbers(db_session, lab):
    c = ctx(db_session, admin=False)
    text = catalogue(c)
    assert text.splitlines()[0].startswith(
        "[1] new upload | new_upload.csv | csv | uploaded 2026-11-19"
    )
    assert "Summary of incident M-045 window." in text
    assert "restricted plan" not in text  # viewers never see restricted documents
    assert len(c.sources.docs) == 3


def test_list_documents_by_upload_date_and_type(db_session, lab):
    c = ctx(db_session)
    assert set(titles(list_documents(c, uploaded_after="2026-11-18"))) == {
        "new upload",
        "restricted plan",
        "incident M-045 window",
    }
    assert titles(list_documents(c, uploaded_before="2026-11-17")) == ["EXP-007 report"]
    assert titles(list_documents(c, file_type="PDF")) == ["EXP-007 report"]


def test_list_documents_by_lab_id_uploader_and_status(db_session, lab):
    c = ctx(db_session)
    assert set(titles(list_documents(c, mentions="m-45"))) == {
        "incident M-045 window",
        "EXP-007 report",
    }
    assert set(titles(list_documents(c, uploaded_by="bob"))) == {
        "EXP-007 report",
        "new upload",
    }
    assert titles(list_documents(c, status="pending")) == ["new upload"]
    result = list_documents(c, title_contains="window")
    assert result["total"] == 1
    assert result["documents"][0]["uploaded_by"] == "Alice Admin"
    assert result["documents"][0]["summary"] == "Summary of incident M-045 window."


def test_viewers_never_get_restricted_documents(db_session, lab):
    c = ctx(db_session, admin=False)
    assert "restricted plan" not in titles(list_documents(c))
    assert collection_stats(c)["total"] == 3
    assert collection_stats(ctx(db_session))["total"] == 4


def test_numbers_are_shared_across_tools(db_session, lab):
    c = ctx(db_session)
    n = list_documents(c, title_contains="incident")["documents"][0]["source"]
    assert lab_id_info(c, "M-045")["documents"][0] == {
        "source": n,
        "title": "incident M-045 window",
        "mentions": 3,
    }


def test_read_document_returns_its_text_with_pages(db_session, lab):
    c = ctx(db_session)
    n = list_documents(c, file_type="pdf")["documents"][0]["source"]
    result = read_document(c, n)
    assert result["text"] == "(page 1)\nPage one.\n---\n(page 2)\nM-045 was excluded."
    assert result["truncated"] is False
    assert len(c.sources.chunk_ids) == 2


def test_search_passages_numbers_and_remembers_passages(db_session, lab):
    c = ctx(db_session, admin=False)  # the restricted "window secrets" is out of reach
    result = search_passages(c, "window clouded")
    assert result["results"][0]["title"] == "incident M-045 window"
    source = c.sources.by_number(result["results"][0]["source"])
    assert source.passage == "The window on M-045 clouded."


def test_collection_stats(db_session, lab):
    stats = collection_stats(ctx(db_session))
    assert stats["by_status"] == {"indexed": 3, "pending": 1}
    assert stats["by_uploader"] == {"Alice Admin": 2, "Bob Biologist": 2}
    assert stats["latest_upload"] == "2026-11-19"


def test_mistakes_come_back_as_errors_the_model_can_fix(db_session, lab):
    c = ctx(db_session)
    assert (
        "Dates must look like"
        in run_tool(c, "list_documents", {"uploaded_after": "last week"})["error"]
    )
    assert "not a lab ID" in run_tool(c, "lab_id_info", {"code": "mouse 42"})["error"]
    assert "No source [99]" in run_tool(c, "read_document", {"source": 99})["error"]
    assert "Unknown tool" in run_tool(c, "delete_everything", {})["error"]
    # nulls from the model's strict schema are simply ignored
    assert (
        result_count(
            run_tool(c, "list_documents", {"file_type": None, "status": "pending"})
        )
        == 1
    )
