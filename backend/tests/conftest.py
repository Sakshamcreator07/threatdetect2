from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app import database
from backend.app.main import create_app


@pytest.fixture()
def test_settings() -> Settings:
    test_root = Path("work") / "test-runs" / uuid4().hex
    test_root.mkdir(parents=True, exist_ok=True)
    return Settings(
        app_env="testing",
        demo_mode=True,
        database_url=f"sqlite:///{test_root / 'test.db'}",
        evidence_storage_dir=test_root / "evidence",
        session_expire_minutes=60,
        session_cookie_secure=False,
        login_max_failed_attempts=3,
        login_lockout_seconds=60,
    )


@pytest.fixture()
def app(test_settings: Settings):
    return create_app(test_settings)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session(app):
    assert database.SessionLocal is not None
    with database.SessionLocal() as db:
        yield db


def login(client: TestClient, username: str = "investigator", password: str = "Admin@123") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["user"]["csrf_token"]
