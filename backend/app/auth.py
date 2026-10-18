from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import log_event
from .config import Settings
from .models import LoginThrottle, SessionRecord, User
from .security import (
    hash_token,
    lockout_expiry,
    new_token,
    now_utc,
    session_expiry,
    verify_password,
)


GENERIC_LOGIN_ERROR = "Invalid credentials."


def _normalize(username: str) -> str:
    return username.strip().lower()


def get_throttle(db: Session, username: str) -> LoginThrottle:
    throttle = db.get(LoginThrottle, username)
    if throttle is None:
        throttle = LoginThrottle(username=username, failed_count=0)
        db.add(throttle)
        db.flush()
    return throttle


def is_locked(throttle: LoginThrottle) -> bool:
    return bool(throttle.locked_until and throttle.locked_until > now_utc())


def record_failed_login(db: Session, username: str, settings: Settings) -> None:
    throttle = get_throttle(db, username)
    throttle.failed_count += 1
    throttle.updated_at = now_utc()
    if throttle.failed_count >= settings.login_max_failed_attempts:
        throttle.locked_until = lockout_expiry(settings.login_lockout_seconds)
        throttle.failed_count = 0


def clear_failed_login(db: Session, username: str) -> None:
    throttle = get_throttle(db, username)
    throttle.failed_count = 0
    throttle.locked_until = None
    throttle.updated_at = now_utc()


def authenticate(db: Session, username: str, password: str, settings: Settings) -> User:
    normalized = _normalize(username)
    throttle = get_throttle(db, normalized)
    if is_locked(throttle):
        log_event(db, action="auth.login", object_type="user", outcome="rejected", object_id=normalized, detail="locked")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    user = db.scalar(select(User).where(User.username == normalized, User.is_active.is_(True)))
    if user is None or not verify_password(password, user.password_hash):
        record_failed_login(db, normalized, settings)
        log_event(db, action="auth.login", object_type="user", outcome="rejected", object_id=normalized)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)

    clear_failed_login(db, normalized)
    log_event(db, action="auth.login", object_type="user", outcome="success", actor=user, object_id=user.id)
    return user


def create_session(db: Session, user: User, settings: Settings) -> tuple[str, str, SessionRecord]:
    token = new_token()
    csrf_token = new_token()
    record = SessionRecord(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_token_hash=hash_token(csrf_token),
        expires_at=session_expiry(settings.session_expire_minutes),
    )
    db.add(record)
    db.flush()
    return token, csrf_token, record


def attach_session_cookies(response: Response, token: str, csrf_token: str, settings: Settings) -> None:
    max_age = settings.session_expire_minutes * 60
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, httponly=True, secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite)
    response.delete_cookie(settings.csrf_cookie_name, httponly=False, secure=settings.session_cookie_secure, samesite=settings.session_cookie_samesite)


def get_session_from_request(db: Session, request: Request, settings: Settings) -> SessionRecord | None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    record = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == hash_token(token)))
    if record is None or record.revoked_at is not None or record.expires_at <= now_utc():
        return None
    return record


def revoke_session(db: Session, session: SessionRecord) -> None:
    session.revoked_at = now_utc()


def require_csrf(request: Request, session: SessionRecord) -> None:
    supplied = request.headers.get("X-CSRF-Token")
    if not supplied or hash_token(supplied) != session.csrf_token_hash:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")


def csrf_token_from_cookie(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.csrf_cookie_name)
