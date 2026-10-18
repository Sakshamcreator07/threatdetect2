from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .audit import log_event
from .config import Settings
from .models import Analysis, AuditLog, Case, Evidence, LoginThrottle, Report, SessionRecord, User
from .security import hash_password


DEMO_USERNAME = "investigator"
DEMO_PASSWORD = "Admin@123"


def require_demo_mode(settings: Settings) -> None:
    settings.validate()
    if not settings.demo_mode:
        raise RuntimeError("Demo data operations require DEMO_MODE=true.")
    if settings.production:
        raise RuntimeError("Demo data operations are blocked in production.")


def seed_demo_account(db: Session, settings: Settings) -> User | None:
    if not settings.demo_mode:
        return None
    require_demo_mode(settings)
    user = db.scalar(select(User).where(User.username == DEMO_USERNAME))
    if user is not None:
        return user
    user = User(
        username=DEMO_USERNAME,
        password_hash=hash_password(DEMO_PASSWORD),
        display_name="Investigator",
        role="Investigator",
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_event(db, action="demo.seed_user", object_type="user", object_id=user.id, outcome="success", actor=user)
    return user


def reset_demo_data(db: Session, settings: Settings) -> None:
    require_demo_mode(settings)
    db.execute(delete(Analysis))
    db.execute(delete(Report))
    db.execute(delete(Evidence))
    db.execute(delete(Case))
    db.execute(delete(SessionRecord))
    db.execute(delete(LoginThrottle))
    db.execute(delete(AuditLog))
    user = db.scalar(select(User).where(User.username == DEMO_USERNAME))
    if user is not None:
        db.delete(user)
        db.flush()
    seed_demo_account(db, settings)


if __name__ == "__main__":
    from .database import SessionLocal, create_all, settings

    create_all()
    assert SessionLocal is not None
    with SessionLocal() as db:
        reset_demo_data(db, settings)
        db.commit()
    print("Demo data reset complete.")
