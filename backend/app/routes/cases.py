from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import auth as auth_service
from ..audit import log_event
from ..database import get_db
from ..dependencies import current_user, require_session
from ..models import Evidence, Report, SessionRecord, User
from ..schemas import CaseCreateRequest, CaseResponse, EvidenceResponse, ReportResponse
from ..services.cases import create_case, get_owned_case, list_cases


router = APIRouter(prefix="/api/cases", tags=["cases"])


def _case_response(case) -> CaseResponse:
    return CaseResponse(
        id=case.id,
        name=case.name,
        description=case.description,
        status=case.status,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("", response_model=list[CaseResponse])
def get_cases(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[CaseResponse]:
    return [_case_response(case) for case in list_cases(db, user)]


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def post_case(
    payload: CaseCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    session: SessionRecord = Depends(require_session),
) -> CaseResponse:
    auth_service.require_csrf(request, session)
    case = create_case(db, user, payload)
    db.commit()
    return _case_response(case)


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> CaseResponse:
    case = get_owned_case(db, user, case_id)
    db.commit()
    return _case_response(case)


@router.get("/{case_id}/evidence", response_model=list[EvidenceResponse])
def get_case_evidence(case_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[EvidenceResponse]:
    get_owned_case(db, user, case_id, audit_action="evidence.list")
    rows = db.scalars(select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.uploaded_at.desc())).all()
    log_event(db, action="evidence.list", object_type="case", object_id=case_id, outcome="success", actor=user)
    db.commit()
    return [
        EvidenceResponse(
            id=e.id,
            case_id=e.case_id,
            evidence_type=e.evidence_type,
            original_filename=e.original_filename,
            mime_type=e.mime_type,
            size_bytes=e.size_bytes,
            sha256=e.sha256,
            uploaded_at=e.uploaded_at,
            metadata_json=e.metadata_json,
        )
        for e in rows
    ]


@router.get("/{case_id}/reports", response_model=list[ReportResponse])
def get_case_reports(case_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[ReportResponse]:
    get_owned_case(db, user, case_id, audit_action="report.list")
    rows = db.scalars(select(Report).where(Report.case_id == case_id).order_by(Report.generated_at.desc())).all()
    log_event(db, action="report.list", object_type="case", object_id=case_id, outcome="success", actor=user)
    db.commit()
    return [
        ReportResponse(
            id=r.id,
            case_id=r.case_id,
            title=r.title,
            generated_at=r.generated_at,
            summary_json=r.summary_json,
        )
        for r in rows
    ]
