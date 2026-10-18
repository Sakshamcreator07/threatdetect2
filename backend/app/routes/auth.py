from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from .. import auth as auth_service
from ..audit import log_event
from ..config import Settings
from ..database import get_db
from ..dependencies import current_user, get_app_settings, require_session
from ..models import SessionRecord, User
from ..schemas import LoginRequest, LoginResponse, UserResponse


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _user_response(user: User, csrf_token: str | None = None) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> LoginResponse:
    try:
        user = auth_service.authenticate(db, payload.username, payload.password, settings)
    except HTTPException:
        db.commit()
        raise
    token, csrf_token, _session = auth_service.create_session(db, user, settings)
    auth_service.attach_session_cookies(response, token, csrf_token, settings)
    db.commit()
    return LoginResponse(user=_user_response(user, csrf_token=csrf_token))


@router.get("/me", response_model=UserResponse)
def me(
    request: Request,
    user: User = Depends(current_user),
    settings: Settings = Depends(get_app_settings),
) -> UserResponse:
    return _user_response(user, csrf_token=auth_service.csrf_token_from_cookie(request, settings))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    session: SessionRecord = Depends(require_session),
) -> None:
    auth_service.require_csrf(request, session)
    user = session.user
    auth_service.revoke_session(db, session)
    log_event(db, action="auth.logout", object_type="session", object_id=session.id, outcome="success", actor=user)
    auth_service.clear_session_cookies(response, settings)
    db.commit()
    return None
