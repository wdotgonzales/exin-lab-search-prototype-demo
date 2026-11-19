import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import SESSION_COOKIE, create_access_token
from app.models import AuditLog, User

T0 = datetime(2026, 11, 19, 6, 0, tzinfo=UTC)


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


@pytest.fixture
def entries(db_session):
    admin = User(
        email="boss@demo.exin", password_hash="x", full_name="Boss", role="admin"
    )
    db_session.add(admin)
    db_session.flush()
    rows = [
        AuditLog(
            action="user.login",
            actor_user_id=admin.id,
            actor_email=admin.email,
            ip_address="203.0.113.24",
            created_at=T0,
        ),
        AuditLog(
            action="user.login_failed",
            actor_email="nobody@example.com",
            ip_address="192.0.2.55",
            created_at=T0 + timedelta(minutes=1),
        ),
        AuditLog(
            action="document.delete",
            actor_user_id=admin.id,
            actor_email=admin.email,
            target_type="document",
            target_id=str(uuid.uuid4()),
            target_label="old.csv",
            metadata_={"file_type": "csv", "size_bytes": 909},
            created_at=T0 + timedelta(minutes=2),
        ),
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


def test_admin_sees_activity_newest_first(client, sign_in, entries):
    sign_in("admin")
    resp = client.get("/api/admin/audit-logs")

    assert resp.status_code == 200
    body = resp.json()
    ours = [
        e
        for e in body["items"]
        if e["actor_email"] in ("boss@demo.exin", "nobody@example.com")
    ]
    assert [e["action"] for e in ours] == [
        "document.delete",
        "user.login_failed",
        "user.login",
    ]
    delete, failed, login = ours
    assert delete["target_label"] == "old.csv"
    assert delete["metadata"] == {"file_type": "csv", "size_bytes": 909}
    assert failed["actor_known"] is False and failed["ip_address"] == "192.0.2.55"
    assert login["actor_known"] is True


def test_group_filter_narrows_to_one_kind(client, sign_in, entries):
    sign_in("admin")
    items = client.get("/api/admin/audit-logs", params={"group": "deletes"}).json()[
        "items"
    ]
    assert {e["action"] for e in items} == {"document.delete"}
    signins = client.get("/api/admin/audit-logs", params={"group": "signins"}).json()[
        "items"
    ]
    assert {e["action"] for e in signins} <= {"user.login", "user.login_failed"}
    assert (
        client.get("/api/admin/audit-logs", params={"group": "nope"}).status_code == 422
    )


def test_viewers_cannot_see_activity(client, sign_in):
    sign_in("viewer")
    assert client.get("/api/admin/audit-logs").status_code == 403
