from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app_env: str
    demo_mode: bool


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    csrf_token: str | None = None


class LoginResponse(BaseModel):
    user: UserResponse


class CaseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)


class CaseResponse(BaseModel):
    id: int
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class EvidenceResponse(BaseModel):
    id: int
    case_id: int
    evidence_type: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    metadata_json: str


class ReportResponse(BaseModel):
    id: int
    case_id: int
    title: str
    generated_at: datetime
    summary_json: str
