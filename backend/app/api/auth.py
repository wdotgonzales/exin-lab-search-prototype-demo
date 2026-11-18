from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, client_ip
from app.config import get_settings
from app.core import audit
from app.core.security import (
    DUMMY_HASH,
    SESSION_COOKIE,
    create_access_token,
    verify_password,
)
from app.models import User
from app.schemas.auth import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_FAILED = "Incorrect email or password."


def _cookie_options() -> dict:
    settings = get_settings()
    return {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
    }


@router.post("/login")
def login(
    body: LoginRequest, request: Request, response: Response, db: DbSession
) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == body.email))
    password_ok = verify_password(
        body.password, user.password_hash if user else DUMMY_HASH
    )
    ip = client_ip(request)

    if user is None or not user.is_active or not password_ok:
        audit.record(
            db,
            "user.login_failed",
            actor_id=user.id if user else None,
            metadata={"email": body.email},
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, LOGIN_FAILED)

    user.last_login_at = datetime.now(UTC)
    audit.record(db, "user.login", actor_id=user.id, ip_address=ip)
    db.commit()

    response.set_cookie(
        SESSION_COOKIE,
        create_access_token(user.id),
        max_age=get_settings().jwt_expire_minutes * 60,
        **_cookie_options(),
    )
    return LoginResponse(user=UserOut.model_validate(user))


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, **_cookie_options())
