from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class DevLoginRequest(BaseModel):
    email: EmailStr = Field(examples=["dev@example.com"])
    display_name: str | None = Field(default="Dev User", examples=["Dev User"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class QuotaInfo(BaseModel):
    search_cache_remaining_today: int
    live_augment_remaining_month: int
    manual_refresh_remaining_month: int


class MeResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    workspace_id: UUID
    plan_tier: str
    quotas: QuotaInfo
