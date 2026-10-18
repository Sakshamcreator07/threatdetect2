from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from backend.app.models import SessionRecord, User
from backend.app.security import now_utc
from .conftest import login


def test_demo_account_initialised_when_demo_mode_enabled(client, db_session):
    user = db_session.scalar(select(User).where(User.username == "investigator"))
    assert user is not None
    assert user.display_name == "Investigator"
    assert user.role == "Investigator"


def test_successful_login_creates_server_session_and_http_only_cookie(client, db_session):
    response = client.post("/api/auth/login", json={"username": "investigator", "password": "Admin@123"})
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "investigator"
    assert response.json()["user"]["csrf_token"]
    assert "dfi_session" in response.cookies
    assert "dfi_csrf" in response.cookies
    assert db_session.scalar(select(SessionRecord)) is not None
    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie


def test_unsuccessful_login_uses_generic_error_for_user_and_password_failures(client):
    unknown = client.post("/api/auth/login", json={"username": "missing", "password": "wrong"})
    wrong_password = client.post("/api/auth/login", json={"username": "investigator", "password": "wrong"})
    assert unknown.status_code == 401
    assert wrong_password.status_code == 401
    assert unknown.json()["detail"] == "Invalid credentials."
    assert wrong_password.json()["detail"] == "Invalid credentials."


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_session_expiry_rejects_request(client, db_session):
    login(client)
    session = db_session.scalar(select(SessionRecord))
    assert session is not None
    session.expires_at = now_utc() - timedelta(seconds=1)
    db_session.commit()
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_logout_invalidates_session(client, db_session):
    csrf = login(client)
    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 204
    session = db_session.scalar(select(SessionRecord))
    db_session.refresh(session)
    assert session.revoked_at is not None
    assert client.get("/api/auth/me").status_code == 401


def test_logout_requires_csrf(client):
    login(client)
    response = client.post("/api/auth/logout")
    assert response.status_code == 403


def test_rate_limiting_and_lockout_are_server_side(client):
    for _ in range(3):
        response = client.post("/api/auth/login", json={"username": "investigator", "password": "wrong"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials."
    response = client.post("/api/auth/login", json={"username": "investigator", "password": "Admin@123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials."
