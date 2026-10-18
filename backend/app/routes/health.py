from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import Settings
from ..dependencies import get_app_settings
from ..schemas import HealthResponse


router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app_env=settings.app_env, demo_mode=settings.demo_mode)
