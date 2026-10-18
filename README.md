# AI Powered Digital Forensics Backend

Phase 1 implements the backend, database, authentication, sessions, audit logging, and initial protected case APIs from the SRS. It does not replace the existing HTML prototype and does not implement the detection engine, file upload pipeline, threat intelligence, encryption at rest, or chain-of-custody completeness.

The original prototype has been copied unchanged to:

```text
frontend\indexers.html
```

When the backend is running, it is also available at:

```text
http://127.0.0.1:8000/prototype/indexers.html
```

## Project Structure

```text
backend/
  app/
    routes/          API route modules
    services/        Business logic
    auth.py          Server-side session and login flow
    audit.py         Audit-log helper
    config.py        Environment settings
    database.py      SQLAlchemy engine/session setup
    demo.py          Demo-only seed/reset utilities
    main.py          FastAPI application factory
    models.py        D1-D5 and audit database models
    schemas.py       Request/response schemas
    security.py      Argon2id password and token helpers
  tests/             Pytest suite
frontend/
  indexers.html      Existing prototype, preserved
scripts/
  reset_demo_data.py Demo-only reset command
data/
  evidence/          Local evidence storage root, not public web content
outputs/
  forensics_platform_audit.md
```

## Windows Setup

From PowerShell in the project folder:

```powershell
cd C:\Users\saksh\Documents\Codex\2026-10-11\i-am-developing-an-ai-powered
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` for local development. Keep these values for the demo account:

```text
APP_ENV=development
DEMO_MODE=true
SESSION_COOKIE_SECURE=false
```

Do not use `DEMO_MODE=true` with `APP_ENV=production`; the application refuses to start in that combination.

## Run The Backend

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Open API documentation:

```text
http://127.0.0.1:8000/docs
```

Open the preserved prototype:

```text
http://127.0.0.1:8000/prototype/indexers.html
```

## Demo Account

The development-only account is seeded only when `DEMO_MODE=true`.

```text
Username: investigator
Password: Admin@123
```

Reset demo data:

```powershell
.\.venv\Scripts\Activate.ps1
python -m scripts.reset_demo_data
```

The reset command is blocked unless demo mode is enabled and the app is not in production.

## API Endpoints In Phase 1

Public:

- `GET /api/health`
- `POST /api/auth/login`

Authenticated:

- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/cases`
- `POST /api/cases`
- `GET /api/cases/{case_id}`
- `GET /api/cases/{case_id}/evidence`
- `GET /api/cases/{case_id}/reports`

State-changing authenticated requests require the `X-CSRF-Token` header. Login returns the token in the response body and also sets a readable CSRF cookie. The session cookie is HttpOnly.

## Run Tests

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest backend\tests -q
```

In this Codex environment, Python package installation was done into `work\pydeps` because the system virtualenv bootstrap and default temp folder were restricted. The exact command used here was:

```powershell
$env:PYTHONPATH=(Resolve-Path work\pydeps).Path + ';' + (Resolve-Path .).Path
$env:TEMP=(Resolve-Path work\manual-scan).Path
$env:TMP=$env:TEMP
python -m pytest backend\tests -q -p no:cacheprovider -p no:tmpdir
```

## Security Status

Implemented in this phase:

- Server-side users in SQLite.
- Argon2id password hashing through `argon2-cffi`.
- Server-managed sessions stored in the database.
- HttpOnly session cookie.
- CSRF token requirement for state-changing protected routes.
- Session expiry and logout invalidation.
- Server-side login lockout and generic authentication errors.
- Case ownership checks on protected case routes.
- Audit-log rows for security-sensitive and case actions.
- D1-D5 database models and relationship constraints.

Not complete yet:

- Encryption at rest.
- Full chain-of-custody workflow.
- Evidence upload API and immutable artifact ingestion.
- External threat intelligence.
- AI/detection pipeline.
- Production deployment hardening and compliance validation.
