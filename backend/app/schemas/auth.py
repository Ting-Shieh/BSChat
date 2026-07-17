from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class DevLoginRequest(BaseModel):
    email: EmailStr = Field(examples=["dev@example.com"])
    display_name: str | None = Field(default="Dev User", examples=["Dev User"])
    plan_tier: str = Field(default="free", examples=["free"], description="free | pro | enterprise")
    seed_org: str | None = Field(default=None, examples=["acme-demo"], description="Dev: attach org + demo stubs")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None
    invite_token: str | None = None


class PasswordLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    sent: bool = True


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class QuotaInfo(BaseModel):
    search_cache_remaining_today: int
    live_augment_remaining_month: int
    manual_refresh_remaining_month: int
    person_linkedin_remaining_month: int
    public_recommend_remaining_lifetime: int = 0
    public_recommend_unlimited: bool = False


class PersonEnrichInfo(BaseModel):
    mode: str  # inference_only | linkedin_llm
    auto_on_url: bool


class AutoRefreshInfo(BaseModel):
    enabled: bool
    interval_days: int


class SearchPrecisionInfo(BaseModel):
    mode: str = Field(description="strict | balanced | exploratory")
    can_use_exploratory: bool = False


class OrgMembershipInfo(BaseModel):
    org_id: UUID
    org_name: str
    role: str
    is_enterprise: bool = False
    is_primary_admin: bool = False


class MeResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    workspace_id: UUID
    plan_tier: str
    quotas: QuotaInfo
    person_enrich: PersonEnrichInfo
    auto_refresh: AutoRefreshInfo
    search_precision: SearchPrecisionInfo
    org_memberships: list[OrgMembershipInfo] = Field(default_factory=list)


class PlanSwitchRequest(BaseModel):
    plan_tier: str = Field(examples=["pro"], description="free | pro | enterprise")


class SettingsUpdateRequest(BaseModel):
    auto_refresh_enabled: bool | None = None
    auto_refresh_interval_days: int | None = Field(default=None, description="30 | 60 | 90")
    person_linkedin_auto_on_url: bool | None = None
    search_precision: str | None = Field(default=None, description="strict | balanced | exploratory")
