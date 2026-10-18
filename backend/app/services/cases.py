from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import log_event
from ..models import Case, User, utcnow
from ..schemas import CaseCreateRequest


def list_cases(db: Session, user: User) -> list[Case]:
    return list(db.scalars(select(Case).where(Case.owner_id == user.id).order_by(Case.created_at.desc())))


def create_case(db: Session, user: User, payload: CaseCreateRequest) -> Case:
    case = Case(
        owner_id=user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        status="Open",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(case)
    db.flush()
    log_event(db, action="case.create", object_type="case", object_id=case.id, outcome="success", actor=user)
    return case


def get_owned_case(db: Session, user: User, case_id: int, *, audit_action: str = "case.view") -> Case:
    case = db.get(Case, case_id)
    if case is None:
        log_event(db, action=audit_action, object_type="case", object_id=case_id, outcome="not_found", actor=user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    if case.owner_id != user.id:
        log_event(db, action=audit_action, object_type="case", object_id=case_id, outcome="forbidden", actor=user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    log_event(db, action=audit_action, object_type="case", object_id=case_id, outcome="success", actor=user)
    return case
