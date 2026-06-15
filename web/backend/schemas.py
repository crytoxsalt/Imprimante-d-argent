from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr


# Auth
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    subscription_tier: str
    created_at: datetime

    class Config:
        from_attributes = True


# Jobs
class JobCreate(BaseModel):
    pipeline: str
    params: dict[str, Any] = {}


class JobResponse(BaseModel):
    id: str
    pipeline: str
    params: dict[str, Any]
    status: str
    output_path: Optional[str]
    error: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Schedules
class ScheduleCreate(BaseModel):
    label: str = ""
    pipeline: str
    params: dict[str, Any] = {}
    cron_expr: str
    auto_upload_account_id: Optional[str] = None


class ScheduleUpdate(BaseModel):
    label: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    cron_expr: Optional[str] = None
    is_active: Optional[bool] = None
    auto_upload_account_id: Optional[str] = None


class ScheduleResponse(BaseModel):
    id: str
    label: str
    pipeline: str
    params: dict[str, Any]
    cron_expr: str
    is_active: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# TikTok Accounts
class TikTokAccountCreate(BaseModel):
    label: str
    cookies_json: str  # raw JSON string, will be encrypted server-side


class TikTokAccountResponse(BaseModel):
    id: str
    label: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Analytics
class AnalyticsSummary(BaseModel):
    total_jobs: int
    jobs_by_pipeline: dict[str, int]
    jobs_last_30_days: list[dict]
    success_rate: float
