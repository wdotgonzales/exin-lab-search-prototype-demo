import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    action: str,
    *,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Add an audit row to the current transaction. The caller commits."""
    db.add(
        AuditLog(
            action=action,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            metadata_=metadata or {},
            ip_address=ip_address,
        )
    )
