"""Write audit records inside the caller's transaction."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import request_id_var
from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    action: str,
    actor_user_id: uuid.UUID | None,
    council_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Add an audit row. It commits (or rolls back) with the action it records."""
    entry = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        council_id=council_id,
        target_type=target_type,
        target_id=target_id,
        details=details or {},
        request_id=request_id_var.get(),
    )
    db.add(entry)
    return entry
