import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.deps import require_admin
from app.core.security import SESSION_COOKIE, hash_password
from app.models import AuditLog, User

PASSWORD = "correct-horse-battery"


@pytest.fixture
def make_user(db_session):
    def _make(email="ana@demo.exin", role="viewer", is_active=True):
        user = User(
            email=email,
            password_hash=hash_password(PASSWORD),
            full_name="Ana Test",
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.flush()
        return user

    return _make


def audit_rows(db_session, action):
    return db_session.scalars(select(AuditLog).where(AuditLog.action == action)).all()


def login(client, email="ana@demo.exin", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_success_sets_cookie_and_audits(client, db_session, make_user):
    user = make_user()
    resp = login(client)

    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "ana@demo.exin"
    assert "password_hash" not in resp.json()["user"]

    cookie = resp.headers["set-cookie"]
    assert f"{SESSION_COOKIE}=" in cookie
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()

    db_session.refresh(user)
    assert user.last_login_at is not None
    rows = audit_rows(db_session, "user.login")
    assert len(rows) == 1
    assert rows[0].actor_user_id == user.id


def test_email_is_case_insensitive(client, make_user):
    make_user()
    assert login(client, email="ANA@Demo.EXIN").status_code == 200


def test_wrong_password_is_401_and_audited(client, db_session, make_user):
    user = make_user()
    resp = login(client, password="wrong")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password."
    assert SESSION_COOKIE not in resp.cookies

    rows = audit_rows(db_session, "user.login_failed")
    assert len(rows) == 1
    assert rows[0].actor_user_id == user.id
    assert rows[0].actor_email == "ana@demo.exin"


@pytest.mark.parametrize("case", ["unknown_email", "disabled_user"])
def test_other_failures_look_identical(client, db_session, make_user, case):
    if case == "unknown_email":
        resp = login(client, email="nobody@demo.exin")
    else:
        make_user(is_active=False)
        resp = login(client)

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password."
    assert len(audit_rows(db_session, "user.login_failed")) == 1


def test_me_requires_a_valid_session(client, make_user):
    assert client.get("/api/auth/me").status_code == 401

    make_user()
    login(client)
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"


def test_tampered_cookie_is_401(client):
    client.cookies.set(SESSION_COOKIE, "not-a-real-token")
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_the_session(client, make_user):
    make_user()
    login(client)

    resp = client.post("/api/auth/logout")
    assert resp.status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_admin_guard(make_user):
    viewer = make_user(email="viewer@demo.exin")
    admin = make_user(email="admin@demo.exin", role="admin")

    with pytest.raises(HTTPException) as exc:
        require_admin(viewer)
    assert exc.value.status_code == 403
    assert require_admin(admin) is admin
