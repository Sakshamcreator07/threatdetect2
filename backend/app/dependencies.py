from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .auth import get_session_from_request
from .config import Settings
from . import database
from .database import get_db
from .models import SessionRecord, User


def get_app_settings() -> Settings:
    return database.settings


def require_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> SessionRecord:
    session = get_session_from_request(db, request, settings)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return session


def current_user(session: SessionRecord = Depends(require_session)) -> User:
    return session.user
