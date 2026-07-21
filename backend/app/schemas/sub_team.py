from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSubTeamRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class SubTeamSummary(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: str | None = None
    role: str
    member_count: int


class SubTeamMemberInfo(BaseModel):
    user_id: UUID
    display_name: str | None
    email: str
    role: str
    joined_at: datetime


class SubTeamDetail(BaseModel):
    id: UUID
    org_id: UUID
    org_name: str
    name: str
    description: str | None = None
    my_role: str | None = None
    member_count: int
    members: list[SubTeamMemberInfo]


class CreateSubTeamInviteRequest(BaseModel):
    expires_days: int = Field(default=14, ge=1, le=90)
    max_uses: int = Field(default=50, ge=1, le=500)


class CreateSubTeamInviteResponse(BaseModel):
    invite_id: UUID
    token: str
    sub_team_id: UUID
    sub_team_name: str
    org_name: str
    expires_at: datetime
    join_path: str


class SubTeamInvitePreview(BaseModel):
    sub_team_id: UUID
    sub_team_name: str
    org_id: UUID
    org_name: str
    expires_at: datetime
    seats_remaining: int


class OrgSubTeamAdminRow(BaseModel):
    id: UUID
    name: str
    member_count: int
    owner_label: str | None
    created_at: datetime
