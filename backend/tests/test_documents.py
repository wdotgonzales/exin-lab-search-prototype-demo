import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.core.security import SESSION_COOKIE, create_access_token
from app.core.storage import LocalStorage, get_storage
from app.main import app
from app.models import AuditLog, Document, Job, User

PDF = b"%PDF-1.7\n%test\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def pdf(n: int) -> bytes:
    return PDF + str(n).encode()  # different bytes -> different hash


@pytest.fixture
def storage(tmp_path):
    local = LocalStorage(tmp_path)
    app.dependency_overrides[get_storage] = lambda: local
    yield local
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
def sign_in(client, db_session):
    def _sign_in(role: str = "admin") -> User:
        user = User(
            email=f"{role}-{uuid.uuid4().hex[:6]}@demo.exin",
            password_hash="not-used",
            full_name=f"{role.title()} Test",
            role=role,
        )
        db_session.add(user)
        db_session.flush()
        client.cookies.set(SESSION_COOKIE, create_access_token(user.id))
        return user

    return _sign_in


def upload(client, *files):
    return client.post(
        "/api/documents",
        files=[
            ("files", (name, data, "application/octet-stream")) for name, data in files
        ],
    )


def test_list_requires_login(client):
    assert client.get("/api/documents").status_code == 401


def test_viewer_can_upload(client, sign_in, storage):
    sign_in("viewer")
    assert upload(client, ("a.pdf", pdf(1))).status_code == 202


def test_upload_writes_document_job_audit_and_file(
    client, db_session, sign_in, storage
):
    admin = sign_in("admin")
    resp = upload(client, ("EXP-007_imaging_notebook.pdf", pdf(1)))

    assert resp.status_code == 202
    body = resp.json()
    assert len(body["accepted"]) == 1
    assert body["skipped"] == [] and body["rejected"] == []
    doc_id = uuid.UUID(body["accepted"][0]["document_id"])

    doc = db_session.get(Document, doc_id)
    assert doc.title == "EXP-007 imaging notebook"
    assert doc.status == "pending"
    assert doc.file_type == "pdf"
    assert doc.uploaded_by == admin.id
    assert doc.external_path == f"uploads/{doc_id}/EXP-007_imaging_notebook.pdf"
    assert storage.read(doc.external_path) == pdf(1)

    job = db_session.scalar(
        select(Job).where(Job.payload["document_id"].astext == str(doc_id))
    )
    assert job.job_type == "ingest_document" and job.status == "queued"

    log = db_session.scalar(select(AuditLog).where(AuditLog.target_id == str(doc_id)))
    assert log.action == "document.upload"
    assert log.actor_email == admin.email
    assert log.target_label == "EXP-007_imaging_notebook.pdf"


def test_duplicates_are_skipped(client, db_session, sign_in, storage):
    sign_in("admin")
    first = upload(client, ("v017.pdf", pdf(1))).json()["accepted"][0]

    again = upload(
        client, ("renamed.pdf", pdf(1)), ("twice.pdf", pdf(2)), ("twice-b.pdf", pdf(2))
    )
    body = again.json()

    assert [s["document_id"] for s in body["skipped"]] == [first["document_id"], None]
    assert len(body["accepted"]) == 1
    assert (
        db_session.scalar(select(Document).where(Document.title == "renamed")) is None
    )


def test_mixed_batch_reports_each_file(client, sign_in, storage):
    sign_in("admin")
    body = upload(
        client, ("ok.pdf", pdf(1)), ("cage.png", PNG), ("fake.pdf", PNG)
    ).json()

    assert [a["filename"] for a in body["accepted"]] == ["ok.pdf"]
    assert {r["filename"] for r in body["rejected"]} == {"cage.png", "fake.pdf"}


def test_too_many_files_rejects_the_request(client, sign_in, storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_files_per_upload", 2)
    sign_in("admin")
    resp = upload(client, ("a.pdf", pdf(1)), ("b.pdf", pdf(2)), ("c.pdf", pdf(3)))
    assert resp.status_code == 422


def test_list_filters_and_pages(client, db_session, sign_in, storage):
    sign_in("admin")
    upload(client, ("C-07_surgery_log.csv", b"mouse\nM-042\n"))
    upload(client, ("V-017_QC_report.pdf", pdf(1)))
    upload(client, ("M-019_headcap_incident.md", b"# M-019\n"))

    # In tests everything runs in one transaction, so now() gives every row the
    # same created_at. Set distinct times so "newest first" is deterministic.
    order = ["C-07_surgery_log.csv", "V-017_QC_report.pdf", "M-019_headcap_incident.md"]
    base = datetime(2026, 11, 18, tzinfo=UTC)
    for doc in db_session.scalars(select(Document)):
        filename = doc.external_path.rsplit("/", 1)[-1]
        doc.created_at = base + timedelta(minutes=order.index(filename))
    db_session.flush()

    everything = client.get("/api/documents").json()
    assert everything["total"] == 3
    assert (
        everything["items"][0]["filename"] == "M-019_headcap_incident.md"
    )  # newest first
    assert everything["items"][0]["uploaded_by_name"] == "Admin Test"

    surgery = client.get("/api/documents", params={"q": "SURGERY"}).json()
    assert surgery["total"] == 1 and surgery["items"][0]["title"] == "C-07 surgery log"

    page2 = client.get("/api/documents", params={"limit": 2, "offset": 2}).json()
    assert page2["total"] == 3 and len(page2["items"]) == 1

    # "%" is matched literally, not as a wildcard
    assert client.get("/api/documents", params={"q": "%"}).json()["total"] == 0


def test_get_one_and_open_file(client, sign_in, storage):
    sign_in("admin")
    doc_id = upload(client, ("notes.pdf", pdf(9))).json()["accepted"][0]["document_id"]
    sign_in("viewer")  # viewers can read what an admin uploaded

    one = client.get(f"/api/documents/{doc_id}")
    assert one.status_code == 200 and one.json()["status"] == "pending"

    file = client.get(f"/api/documents/{doc_id}/file")
    assert file.status_code == 200
    assert file.content == pdf(9)
    assert file.headers["content-type"] == "application/pdf"
    assert file.headers["content-disposition"].startswith("inline;")

    assert client.get(f"/api/documents/{uuid.uuid4()}").status_code == 404


def delete_docs(client, ids):
    return client.post(
        "/api/documents/delete", json={"document_ids": [str(i) for i in ids]}
    )


def test_admin_hard_deletes_rows_files_and_audits(client, db_session, sign_in, storage):
    admin = sign_in("admin")
    body = upload(client, ("a.pdf", pdf(1)), ("b.pdf", pdf(2))).json()
    ids = [uuid.UUID(a["document_id"]) for a in body["accepted"]]
    paths = [db_session.get(Document, i).external_path for i in ids]
    missing = uuid.uuid4()

    resp = delete_docs(client, [*ids, missing])

    assert resp.status_code == 200
    assert resp.json() == {
        "deleted": [str(i) for i in ids],
        "not_found": [str(missing)],
    }
    db_session.expire_all()
    for doc_id, path in zip(ids, paths, strict=True):
        assert db_session.get(Document, doc_id) is None
        with pytest.raises(FileNotFoundError):
            storage.read(path)
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.target_id == str(doc_id), AuditLog.action == "document.delete"
            )
        )
        assert log.actor_email == admin.email
        assert log.target_label == path.rsplit("/", 1)[-1]


def test_viewer_cannot_delete(client, db_session, sign_in, storage):
    sign_in("viewer")
    body = upload(client, ("a.pdf", pdf(1))).json()
    doc_id = uuid.UUID(body["accepted"][0]["document_id"])

    assert delete_docs(client, [doc_id]).status_code == 403
    db_session.expire_all()
    assert db_session.get(Document, doc_id) is not None


def test_delete_needs_1_to_50_ids(client, sign_in, storage):
    sign_in("admin")
    assert delete_docs(client, []).status_code == 422
    assert delete_docs(client, [uuid.uuid4() for _ in range(51)]).status_code == 422
