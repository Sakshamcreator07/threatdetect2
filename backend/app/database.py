from __future__ import annotations

from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings, get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    raw_path = database_url.replace("sqlite:///", "", 1)
    if raw_path == ":memory:":
        return
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


def configure_database(new_settings: Settings | None = None) -> None:
    global settings, engine, SessionLocal
    if new_settings is not None:
        new_settings.validate()
        settings = new_settings
    _ensure_sqlite_parent(settings.database_url)
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
    if settings.database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def create_all() -> None:
    if engine is None:
        configure_database()
    from . import models  # noqa: F401
    assert engine is not None
    Base.metadata.create_all(bind=engine)


def drop_all() -> None:
    if engine is None:
        configure_database()
    from . import models  # noqa: F401
    assert engine is not None
    Base.metadata.drop_all(bind=engine)


def get_db() -> Iterator[Session]:
    if SessionLocal is None:
        configure_database()
    assert SessionLocal is not None
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


configure_database()
