from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession
from app.models import AuditLog
from app.schemas.admin import AuditEntryOut, AuditLogList

router = APIRouter(prefix="/admin", tags=["admin"])

# The page's filter buttons, mapped to the actions they cover
GROUPS: dict[str, tuple[str, ...]] = {
    "signins": ("user.login", "user.login_failed"),
    "uploads": ("document.upload",),
    "deletes": ("document.delete",),
    "accounts": ("user.created",),
}
Group = Literal["signins", "uploads", "deletes", "accounts"]


def _out(entry: AuditLog) -> AuditEntryOut:
    return AuditEntryOut(
        id=entry.id,
        created_at=entry.created_at,
        actor_email=entry.actor_email,
        actor_known=entry.actor_user_id is not None,
        action=entry.action,
        target_type=entry.target_type,
        target_label=entry.target_label,
        metadata=entry.metadata_ or {},
        ip_address=str(entry.ip_address) if entry.ip_address else None,
    )


@router.get("/audit-logs")
def list_audit_logs(
    admin: AdminUser,
    db: DbSession,
    group: Group | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogList:
    """The activity history, newest first. Read-only: entries are never changed."""
    stmt = select(AuditLog)
    count = select(func.count()).select_from(AuditLog)
    if group:
        stmt = stmt.where(AuditLog.action.in_(GROUPS[group]))
        count = count.where(AuditLog.action.in_(GROUPS[group]))
    rows = db.scalars(
        stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return AuditLogList(items=[_out(r) for r in rows], total=db.scalar(count) or 0)
