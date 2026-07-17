from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateTeamRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100)


class TeamResponse(BaseModel):
    org_id: UUID
    org_name: str
    slug: str


class CreateInviteRequest(BaseModel):
    org_id: UUID
    expires_days: int = Field(default=14, ge=1, le=90)
    max_uses: int = Field(default=50, ge=1, le=500)


class CreateInviteResponse(BaseModel):
    invite_id: UUID
    token: str
    org_id: UUID
    org_name: str
    expires_at: datetime
    max_uses: int
    join_path: str


class InvitePreviewResponse(BaseModel):
    org_id: UUID
    org_name: str
    slug: str
    expires_at: datetime
    seats_remaining: int
