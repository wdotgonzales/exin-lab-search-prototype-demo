"""Background worker: turns queued uploads into searchable chunks.

Run with:  python -m app.worker

One loop, forever:
  1. claim the oldest due job (FOR UPDATE SKIP LOCKED, so several workers
     never take the same job)
  2. read the file from storage, extract text, find lab IDs, chunk, embed
  3. save chunks + lab IDs and mark the document "indexed", in one transaction

On failure: an unreadable file fails at once with a reason users can read.
Anything else (S3, network, OpenAI) is retried after 1 minute, then
5 minutes, and fails after the job's max_attempts (3).
"""

import logging
import signal
import threading
import time
import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.storage import Storage, get_storage
from app.db import SessionLocal
from app.ingest.chunking import chunk_sections
from app.ingest.embedder import Embedder, get_embedder
from app.ingest.extract import ExtractionError, extract
from app.ingest.lab_ids import find_lab_ids
from app.models import Chunk, Document, DocumentEntity, Entity, Job

log = logging.getLogger("app.worker")

POLL_SECONDS = 2.0
SWEEP_SECONDS = 60.0
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5))
STALE_AFTER = timedelta(minutes=15)
GAVE_UP = "Couldn't index this file after several tries. Ask an admin to re-index it."


# ── claiming ────────────────────────────────────────────────────


def next_due_job(db: Session) -> Job | None:
    """Lock the oldest due job. Rows locked by other workers are skipped."""
    return db.scalars(
        select(Job)
        .where(Job.status == "queued", Job.run_after <= func.now())
        .order_by(Job.run_after, Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).first()


def claim_job(db: Session) -> Job | None:
    """Take the oldest due job and mark it running. Commits."""
    job = next_due_job(db)
    if job is None:
        db.rollback()  # end the read transaction
        return None
    job.status = "running"
    job.locked_at = func.now()
    job.attempts += 1
    db.commit()
    return job


# ── processing ──────────────────────────────────────────────────


def run_once(db: Session, storage: Storage, embedder: Embedder) -> bool:
    """Process one job. Returns False when there was nothing to do."""
    job = claim_job(db)
    if job is None:
        return False
    job_id = job.id
    log.info("job %s: %s (attempt %s)", job_id, job.job_type, job.attempts)
    try:
        if job.job_type != "ingest_document":
            raise ExtractionError(f"Unsupported job type: {job.job_type}")
        ingest_document(db, job, storage, embedder)
    except ExtractionError as exc:
        log.info("job %s: file can't be indexed: %s", job_id, exc)
        _record_failure(db, job_id, str(exc), user_message=str(exc), retry=False)
    except Exception as exc:
        log.exception("job %s failed", job_id)
        _record_failure(db, job_id, repr(exc), user_message=GAVE_UP, retry=True)
    return True


def ingest_document(
    db: Session, job: Job, storage: Storage, embedder: Embedder
) -> None:
    doc = db.get(Document, uuid.UUID(job.payload["document_id"]))
    if doc is None:  # deleted after upload: nothing to do
        _succeed(job, note="Document was deleted before it was indexed")
        db.commit()
        return

    doc.status = "processing"  # the table shows "Indexing…" while we work
    doc.error_message = None
    db.commit()

    sections = extract(doc.file_type, storage.read(doc.external_path))
    drafts = chunk_sections(sections)
    vectors = embedder.embed([d.content for d in drafts])
    lab_ids = find_lab_ids("\n".join(s.text for s in sections))

    # Replace, never append: re-indexing must not create duplicates.
    db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
    db.execute(delete(DocumentEntity).where(DocumentEntity.document_id == doc.id))
    db.add_all(
        Chunk(
            document_id=doc.id,
            chunk_index=draft.index,
            content=draft.content,
            token_count=draft.token_count,
            page_number=draft.page,
            embedding=vector,
            embedding_model=embedder.model,
        )
        for draft, vector in zip(drafts, vectors, strict=True)
    )
    if lab_ids:
        db.execute(
            insert(Entity)
            .values([{"code": i.code, "entity_type": i.entity_type} for i in lab_ids])
            .on_conflict_do_nothing(index_elements=["code"])
        )
        ids = dict(
            db.execute(
                select(Entity.code, Entity.id).where(
                    Entity.code.in_([i.code for i in lab_ids])
                )
            ).all()
        )
        db.execute(
            insert(DocumentEntity).values(
                [
                    {
                        "document_id": doc.id,
                        "entity_id": ids[i.code],
                        "mention_count": n,
                    }
                    for i, n in lab_ids.items()
                ]
            )
        )

    doc.status = "indexed"
    doc.indexed_at = func.now()
    _succeed(job)
    db.commit()
    log.info("job %s: indexed %s (%d chunks)", job.id, doc.title, len(drafts))


def _succeed(job: Job, note: str | None = None) -> None:
    job.status = "succeeded"
    job.finished_at = func.now()
    job.last_error = note


# ── failures ────────────────────────────────────────────────────


def _apply_failure(
    db: Session, job: Job, detail: str, user_message: str, retry: bool
) -> None:
    doc_id = job.payload.get("document_id")
    doc = db.get(Document, uuid.UUID(doc_id)) if doc_id else None
    job.last_error = detail[:2000]
    job.locked_at = None
    if retry and job.attempts < job.max_attempts:
        delay = RETRY_DELAYS[min(job.attempts, len(RETRY_DELAYS)) - 1]
        job.status = "queued"
        job.run_after = func.now() + delay
        if doc is not None:
            doc.status = "pending"
    else:
        job.status = "failed"
        job.finished_at = func.now()
        if doc is not None:
            doc.status = "failed"
            doc.error_message = user_message


def _record_failure(
    db: Session, job_id: int, detail: str, user_message: str, retry: bool
) -> None:
    db.rollback()  # throw away anything half-saved by this attempt
    job = db.get(Job, job_id)
    if job is not None:
        _apply_failure(db, job, detail, user_message, retry)
        db.commit()


def requeue_stale(db: Session) -> int:
    """Jobs left 'running' by a worker that crashed or was killed mid-job."""
    stale = db.scalars(
        select(Job)
        .where(Job.status == "running", Job.locked_at < func.now() - STALE_AFTER)
        .with_for_update(skip_locked=True)
    ).all()
    for job in stale:
        _apply_failure(
            db, job, "Worker stopped while processing this job", GAVE_UP, retry=True
        )
    db.commit()
    return len(stale)


# ── the loop ────────────────────────────────────────────────────


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):  # docker stop / Ctrl+C
        signal.signal(sig, lambda *_: stop.set())

    storage, embedder = get_storage(), get_embedder()
    log.info("worker started (embedder: %s)", embedder.model)
    last_sweep = 0.0
    while not stop.is_set():
        worked = False
        try:
            with SessionLocal() as db:
                if time.monotonic() - last_sweep > SWEEP_SECONDS:
                    if count := requeue_stale(db):
                        log.warning("requeued %d stale job(s)", count)
                    last_sweep = time.monotonic()
                worked = run_once(db, storage, embedder)
        except Exception:  # e.g. the database is briefly unreachable
            log.exception("worker loop error; retrying shortly")
        if not worked:
            stop.wait(POLL_SECONDS)  # idle: wait, but wake up at once on stop
    log.info("worker stopped")


if __name__ == "__main__":
    main()
