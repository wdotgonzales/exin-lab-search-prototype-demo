import hashlib
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import delete, func, select

from app.core.storage import LocalStorage
from app.db import SessionLocal
from app.ingest.embedder import FakeEmbedder
from app.models import Chunk, Document, DocumentEntity, Entity, Job, Source
from app.models.source import UPLOAD_SOURCE_NAME
from app.worker import claim_job, next_due_job, requeue_stale, run_once

TEXT = b"Mouse M-042 was injected with V-019 for EXP-007.\n\nM-042 recovered well."


class BrokenEmbedder:
    """Stands in for OpenAI being down."""

    model = "broken"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise ConnectionError("OpenAI is down")


@pytest.fixture
def storage(tmp_path):
    return LocalStorage(tmp_path)


def add_document(db, storage, data: bytes = TEXT) -> tuple[Document, Job]:
    """What an upload creates: the file in storage, a document and a job."""
    source = db.scalar(select(Source).where(Source.name == UPLOAD_SOURCE_NAME))
    doc_id = uuid.uuid4()
    key = f"uploads/{doc_id}/notes.txt"
    storage.put(key, data, "text/plain")
    doc = Document(
        id=doc_id,
        source_id=source.id,
        external_path=key,
        title="notes",
        file_type="txt",
        size_bytes=len(data),
        content_hash=hashlib.sha256(data).hexdigest(),
    )
    job = Job(job_type="ingest_document", payload={"document_id": str(doc_id)})
    db.add_all([doc, job])
    db.commit()
    return doc, job


def count(db, model, document_id) -> int:
    return db.scalar(
        select(func.count()).select_from(model).where(model.document_id == document_id)
    )


def test_indexes_a_document(db_session, storage):
    doc, job = add_document(db_session, storage)

    assert run_once(db_session, storage, FakeEmbedder()) is True

    db_session.refresh(doc)
    db_session.refresh(job)
    assert (doc.status, doc.error_message) == ("indexed", None)
    assert doc.indexed_at is not None
    assert (job.status, job.attempts, job.last_error) == ("succeeded", 1, None)

    [chunk] = db_session.scalars(select(Chunk).where(Chunk.document_id == doc.id))
    assert "M-042 recovered well." in chunk.content
    assert chunk.embedding_model == "fake-hash-v1"
    assert len(chunk.embedding) == 1536

    mentions = dict(
        db_session.execute(
            select(Entity.code, DocumentEntity.mention_count)
            .select_from(Entity)
            .join(DocumentEntity)
            .where(DocumentEntity.document_id == doc.id)
        ).all()
    )
    assert mentions == {"M-042": 2, "V-019": 1, "EXP-007": 1}

    assert run_once(db_session, storage, FakeEmbedder()) is False  # queue is empty


def test_reindexing_replaces_instead_of_duplicating(db_session, storage):
    doc, job = add_document(db_session, storage)
    run_once(db_session, storage, FakeEmbedder())
    job.status = "queued"
    db_session.commit()

    run_once(db_session, storage, FakeEmbedder())

    assert count(db_session, Chunk, doc.id) == 1
    assert count(db_session, DocumentEntity, doc.id) == 3


def test_unreadable_file_fails_at_once_with_a_reason(db_session, storage):
    doc, job = add_document(db_session, storage, data=b"   \n")

    run_once(db_session, storage, FakeEmbedder())

    db_session.refresh(doc)
    db_session.refresh(job)
    assert doc.status == "failed"
    assert "No readable text" in doc.error_message
    assert (job.status, job.attempts) == ("failed", 1)  # no pointless retries
    assert job.finished_at is not None


def test_temporary_errors_retry_then_give_up(db_session, storage):
    doc, job = add_document(db_session, storage)

    run_once(db_session, storage, BrokenEmbedder())

    db_session.refresh(doc)
    db_session.refresh(job)
    assert (job.status, job.attempts, doc.status) == ("queued", 1, "pending")
    assert "OpenAI is down" in job.last_error
    assert job.run_after > db_session.scalar(select(func.now()))
    assert run_once(db_session, storage, FakeEmbedder()) is False  # not due yet

    for _ in range(2):  # pretend each wait is over, and fail again
        job.run_after = func.now()
        db_session.commit()
        run_once(db_session, storage, BrokenEmbedder())

    db_session.refresh(doc)
    db_session.refresh(job)
    assert (job.status, job.attempts) == ("failed", 3)
    assert doc.status == "failed"
    assert "after several tries" in doc.error_message
    assert count(db_session, Chunk, doc.id) == 0  # nothing half-saved


def test_job_for_a_deleted_document_is_skipped(db_session, storage):
    doc, job = add_document(db_session, storage)
    db_session.delete(doc)
    db_session.commit()

    assert run_once(db_session, storage, FakeEmbedder()) is True

    db_session.refresh(job)
    assert job.status == "succeeded"
    assert "deleted" in job.last_error


def test_stale_running_job_is_requeued(db_session, storage):
    doc, job = add_document(db_session, storage)
    claim_job(db_session)  # a worker took it ... and then crashed
    job.locked_at = func.now() - timedelta(hours=1)
    db_session.commit()

    assert requeue_stale(db_session) == 1

    db_session.refresh(job)
    db_session.refresh(doc)
    assert (job.status, doc.status) == ("queued", "pending")
    assert "Worker stopped" in job.last_error


def test_two_workers_never_get_the_same_job():
    """Uses real commits instead of the rollback fixture: row locks only
    matter between two separate database connections."""
    with SessionLocal() as setup:
        jobs = [Job(job_type="ingest_document", payload={}) for _ in range(2)]
        setup.add_all(jobs)
        setup.commit()
        ids = {j.id for j in jobs}

    worker_a, worker_b = SessionLocal(), SessionLocal()
    try:
        held_by_a = next_due_job(worker_a)  # A holds a row lock, transaction open
        claimed_by_b = claim_job(worker_b)  # B must skip A's row
        assert held_by_a is not None
        assert claimed_by_b is not None
        assert {held_by_a.id, claimed_by_b.id} == ids
    finally:
        worker_a.rollback()
        worker_a.close()
        worker_b.close()
        with SessionLocal() as cleanup:
            cleanup.execute(delete(Job).where(Job.id.in_(ids)))
            cleanup.commit()
