from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .database import configure_database, create_all
from .demo import seed_demo_account
from .routes import auth, cases, health


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()
    settings.validate()
    settings.evidence_storage_dir.mkdir(parents=True, exist_ok=True)
    configure_database(settings)
    create_all()

    app = FastAPI(title="AI Digital Forensics Backend", version="0.1.0")
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(cases.router)
    app.mount("/prototype", StaticFiles(directory="frontend", html=True), name="prototype")

    if settings.demo_mode:
        from .database import SessionLocal

        assert SessionLocal is not None
        with SessionLocal() as db:
            seed_demo_account(db, settings)
            db.commit()

    return app


app = create_app()
