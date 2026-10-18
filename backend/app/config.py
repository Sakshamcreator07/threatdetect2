from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    demo_mode: bool = False
    database_url: str = "sqlite:///./data/forensics_dev.db"
    evidence_storage_dir: Path = Path("./data/evidence")
    session_cookie_name: str = "dfi_session"
    csrf_cookie_name: str = "dfi_csrf"
    session_expire_minutes: int = 60
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    login_max_failed_attempts: int = 5
    login_lockout_seconds: int = 900

    @property
    def production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate(self) -> None:
        if self.production and self.demo_mode:
            raise RuntimeError("DEMO_MODE=true is not allowed when APP_ENV=production.")
        if self.production and not self.session_cookie_secure:
            raise RuntimeError("SESSION_COOKIE_SECURE must be true when APP_ENV=production.")
        if self.session_expire_minutes <= 0:
            raise RuntimeError("SESSION_EXPIRE_MINUTES must be positive.")
        if self.login_max_failed_attempts <= 0:
            raise RuntimeError("LOGIN_MAX_FAILED_ATTEMPTS must be positive.")
        if self.login_lockout_seconds <= 0:
            raise RuntimeError("LOGIN_LOCKOUT_SECONDS must be positive.")


def get_settings() -> Settings:
    load_dotenv()
    settings = Settings(
        app_env=os.getenv("APP_ENV", "development"),
        demo_mode=_bool(os.getenv("DEMO_MODE"), False),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/forensics_dev.db"),
        evidence_storage_dir=Path(os.getenv("EVIDENCE_STORAGE_DIR", "./data/evidence")),
        session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "dfi_session"),
        csrf_cookie_name=os.getenv("CSRF_COOKIE_NAME", "dfi_csrf"),
        session_expire_minutes=_int("SESSION_EXPIRE_MINUTES", 60),
        session_cookie_secure=_bool(os.getenv("SESSION_COOKIE_SECURE"), False),
        session_cookie_samesite=os.getenv("SESSION_COOKIE_SAMESITE", "lax"),
        login_max_failed_attempts=_int("LOGIN_MAX_FAILED_ATTEMPTS", 5),
        login_lockout_seconds=_int("LOGIN_LOCKOUT_SECONDS", 900),
    )
    settings.validate()
    return settings
