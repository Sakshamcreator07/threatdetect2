from __future__ import annotations

from sqlalchemy.orm import Session

from .models import AuditLog, User


def log_event(
    db: Session,
    *,
    action: str,
    object_type: str,
    outcome: str,
    actor: User | None = None,
    object_id: str | int | None = None,
    detail: str = "",
) -> AuditLog:
    event = AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else None,
        outcome=outcome,
        detail=detail,
    )
    db.add(event)
    return event
