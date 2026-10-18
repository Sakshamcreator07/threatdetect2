from __future__ import annotations

import pytest
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.models import Analysis, AuditLog, Case, Evidence, Report, User
from backend.app.security import hash_password
from .conftest import login


def test_protected_case_routes_reject_unauthenticated_requests(client):
    assert client.get("/api/cases").status_code == 401
    assert client.get("/api/cases/1").status_code == 401
    assert client.get("/api/cases/1/evidence").status_code == 401
    assert client.get("/api/cases/1/reports").status_code == 401


def test_case_creation_and_retrieval(client, db_session):
    csrf = login(client)
    create = client.post(
        "/api/cases",
        json={"name": "Phishing Case", "description": "Suspicious email campaign"},
        headers={"X-CSRF-Token": csrf},
    )
    assert create.status_code == 201, create.text
    case_id = create.json()["id"]
    assert create.json()["status"] == "Open"

    listed = client.get("/api/cases")
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [case_id]

    fetched = client.get(f"/api/cases/{case_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Phishing Case"

    audit_actions = [row.action for row in db_session.scalars(select(AuditLog)).all()]
    assert "case.create" in audit_actions
    assert "case.view" in audit_actions


def test_case_post_requires_csrf(client):
    login(client)
    response = client.post("/api/cases", json={"name": "No CSRF", "description": ""})
    assert response.status_code == 403


def test_case_isolation_between_users(client, db_session):
    csrf = login(client)
    create = client.post("/api/cases", json={"name": "Owner Case", "description": ""}, headers={"X-CSRF-Token": csrf})
    assert create.status_code == 201
    case_id = create.json()["id"]
    client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})

    other = User(
        username="other",
        password_hash=hash_password("Secret123"),
        display_name="Other User",
        role="Investigator",
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()

    login(client, "other", "Secret123")
    assert client.get(f"/api/cases/{case_id}").status_code == 404
    assert client.get("/api/cases").json() == []


def test_evidence_analysis_and_report_relationship_constraints(db_session):
    user = db_session.scalar(select(User).where(User.username == "investigator"))
    case_one = Case(owner_id=user.id, name="Case One", description="")
    case_two = Case(owner_id=user.id, name="Case Two", description="")
    db_session.add_all([case_one, case_two])
    db_session.flush()

    evidence = Evidence(
        case_id=case_one.id,
        uploaded_by_id=user.id,
        evidence_type="file",
        original_filename="sample.txt",
        mime_type="text/plain",
        size_bytes=12,
        sha256="a" * 64,
        storage_path="data/evidence/sample.txt",
    )
    db_session.add(evidence)
    db_session.flush()

    analysis = Analysis(
        case_id=case_one.id,
        evidence_id=evidence.id,
        risk_score=0,
        risk_level="clean",
        verdict="Clean",
    )
    report = Report(case_id=case_one.id, generated_by_id=user.id, title="Initial Report")
    db_session.add_all([analysis, report])
    db_session.commit()

    bad_analysis = Analysis(case_id=case_two.id, evidence_id=evidence.id, risk_score=10, risk_level="low", verdict="Low")
    db_session.add(bad_analysis)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    bad_evidence = Evidence(
        case_id=999999,
        uploaded_by_id=user.id,
        evidence_type="file",
        original_filename="orphan.txt",
        mime_type="text/plain",
        size_bytes=1,
        sha256="b" * 64,
        storage_path="data/evidence/orphan.txt",
    )
    db_session.add(bad_evidence)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_case_evidence_and_report_lists_are_owned(client, db_session):
    csrf = login(client)
    case_response = client.post("/api/cases", json={"name": "Linked Records", "description": ""}, headers={"X-CSRF-Token": csrf})
    case_id = case_response.json()["id"]
    user = db_session.scalar(select(User).where(User.username == "investigator"))
    evidence = Evidence(
        case_id=case_id,
        uploaded_by_id=user.id,
        evidence_type="url",
        original_filename="https://example.com",
        mime_type="text/uri-list",
        size_bytes=19,
        sha256="c" * 64,
        storage_path="data/evidence/url.txt",
    )
    report = Report(case_id=case_id, generated_by_id=user.id, title="Case Report")
    db_session.add_all([evidence, report])
    db_session.commit()

    evidence_response = client.get(f"/api/cases/{case_id}/evidence")
    reports_response = client.get(f"/api/cases/{case_id}/reports")
    assert evidence_response.status_code == 200
    assert reports_response.status_code == 200
    assert evidence_response.json()[0]["case_id"] == case_id
    assert reports_response.json()[0]["case_id"] == case_id


def test_cases_persist_after_application_restart():
    test_root = Path("work") / "test-runs" / f"restart-{uuid4().hex}"
    test_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        app_env="testing",
        demo_mode=True,
        database_url=f"sqlite:///{test_root / 'restart.db'}",
        evidence_storage_dir=test_root / "evidence",
        session_cookie_secure=False,
        login_max_failed_attempts=3,
        login_lockout_seconds=60,
    )

    first_app = create_app(settings)
    with TestClient(first_app) as first_client:
        csrf = login(first_client)
        created = first_client.post(
            "/api/cases",
            json={"name": "Persistent Case", "description": "Survives app recreation"},
            headers={"X-CSRF-Token": csrf},
        )
        assert created.status_code == 201
        case_id = created.json()["id"]

    second_app = create_app(settings)
    with TestClient(second_app) as second_client:
        login(second_client)
        listed = second_client.get("/api/cases")
        assert listed.status_code == 200
        assert any(row["id"] == case_id and row["name"] == "Persistent Case" for row in listed.json())
