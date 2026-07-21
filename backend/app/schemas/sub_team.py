from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


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
    email: EmailStr
    expires_days: int = Field(default=14, ge=1, le=90)


class CreateSubTeamInviteResponse(BaseModel):
    invite_id: UUID
    token: str
    sub_team_id: UUID
    sub_team_name: str
    org_name: str
    invited_email: str
    expires_at: datetime
    join_path: str
    email_sent: bool


InviteStatus = Literal["pending", "accepted", "revoked", "expired"]


class SubTeamInviteListItem(BaseModel):
    invite_id: UUID
    invited_email: str | None
    status: InviteStatus
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
    use_count: int
    max_uses: int


class SubTeamInvitePreview(BaseModel):
    sub_team_id: UUID
    sub_team_name: str
    org_id: UUID
    org_name: str
    invited_email: str | None = None
    expires_at: datetime
    seats_remaining: int


class OrgSubTeamAdminRow(BaseModel):
    id: UUID
    name: str
    member_count: int
    owner_label: str | None
    created_at: datetime


class NotificationItem(BaseModel):
    id: UUID
    kind: str
    title: str
    body: str | None
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int
