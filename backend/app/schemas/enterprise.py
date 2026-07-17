from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class EnterpriseApplicationCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    contact_email: EmailStr
    slug_requested: str | None = Field(default=None, max_length=100)
    estimated_seats: int | None = Field(default=None, ge=1, le=10000)
    note: str | None = Field(default=None, max_length=2000)


class EnterpriseApplicationResponse(BaseModel):
    id: UUID
    company_name: str
    slug_requested: str | None
    contact_email: str
    estimated_seats: int | None
    note: str | None
    status: str
    resulting_org_id: UUID | None
    created_at: datetime
    reviewed_at: datetime | None


class ProvisionEnterpriseRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100)
    admin_email: EmailStr
    seat_limit: int | None = Field(default=None, ge=1, le=10000)


class ProvisionEnterpriseResponse(BaseModel):
    org_id: UUID
    org_name: str
    slug: str
    primary_admin_user_id: UUID
    is_enterprise: bool = True


class ApproveApplicationRequest(BaseModel):
    slug_override: str | None = Field(default=None, max_length=100)
    seat_limit: int | None = Field(default=None, ge=1, le=10000)
    reviewed_by: str = Field(default="ops", max_length=128)


class RejectApplicationRequest(BaseModel):
    reviewed_by: str = Field(default="ops", max_length=128)


class EnterpriseOrgSummary(BaseModel):
    org_id: UUID
    org_name: str
    slug: str
    is_enterprise: bool
    primary_admin_user_id: UUID | None
    seat_limit: int | None
    member_count: int
    approved_at: datetime | None


class EnterpriseMemberInfo(BaseModel):
    user_id: UUID
    email: str
    display_name: str | None
    role: str
    is_primary_admin: bool
    joined_at: datetime


class CreateEnterpriseInviteRequest(BaseModel):
    email: EmailStr
    expires_days: int = Field(default=14, ge=1, le=90)


class CreateEnterpriseInviteResponse(BaseModel):
    invite_id: UUID
    token: str
    org_id: UUID
    org_name: str
    invited_email: str
    expires_at: datetime
    join_path: str
    email_sent: bool


class EnterpriseInvitePreview(BaseModel):
    org_id: UUID
    org_name: str
    slug: str
    invited_email: str | None
    expires_at: datetime
    is_enterprise: bool = True


class EnterpriseInviteListItem(BaseModel):
    invite_id: UUID
    invited_email: str | None
    expires_at: datetime
    use_count: int
    max_uses: int
    revoked_at: datetime | None
    created_at: datetime


class TransferAdminRequest(BaseModel):
    new_admin_user_id: UUID
