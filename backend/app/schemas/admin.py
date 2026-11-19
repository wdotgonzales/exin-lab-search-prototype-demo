import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    actor_email: str | None
    actor_known: bool  # the actor is a real account (false: unknown email or the CLI)
    action: str
    target_type: str | None
    target_label: str | None
    metadata: dict[str, Any]
    ip_address: str | None


class AuditLogList(BaseModel):
    items: list[AuditEntryOut]
    total: int
