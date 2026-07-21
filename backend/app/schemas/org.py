from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrgMembershipInfo(BaseModel):
    org_id: UUID
    org_name: str
    role: str


class OrgSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    published_stub_count: int = 0


class OrgListResponse(BaseModel):
    items: list[OrgSummary]


class StubCreateRequest(BaseModel):
    display_name: str
    company_name: str
    title: str | None = None
    responsibility_keywords: list[str] = Field(default_factory=list)
    product_keywords: list[str] = Field(default_factory=list)
    external_card_url: str | None = None
    one_line_blurb: str | None = None
    avatar_url: str | None = None
    # Enterprise default: publish into public pool on create (opt-out via false).
    allow_ai_recommend: bool = True
    # Account this identity belongs to (required for exposure under DDR-v4-15).
    owner_user_id: UUID | None = None


class StubUpdateRequest(BaseModel):
    display_name: str | None = None
    company_name: str | None = None
    title: str | None = None
    responsibility_keywords: list[str] | None = None
    product_keywords: list[str] | None = None
    external_card_url: str | None = None
    one_line_blurb: str | None = None
    avatar_url: str | None = None
    owner_user_id: UUID | None = None
    want_ai_recommend: bool | None = None


class StubResponse(BaseModel):
    id: UUID
    org_id: UUID
    display_name: str
    company_name: str
    title: str | None
    responsibility_keywords: list[str]
    product_keywords: list[str]
    external_card_url: str | None = None
    one_line_blurb: str | None = None
    avatar_url: str | None = None
    status: str
    want_ai_recommend: bool = True
    published_at: datetime | None
    unpublished_at: datetime | None
    created_at: datetime
    updated_at: datetime
    share_path: str | None = None
    owner_user_id: UUID | None = None


class MyPublicIdentityResponse(BaseModel):
    org_id: UUID
    org_name: str
    stub_id: UUID | None = None
    display_name: str | None = None
    title: str | None = None
    external_card_url: str | None = None
    status: str | None = None
    want_ai_recommend: bool = True
    ai_state: str  # pending_invite N/A | pending_url | on | off


class MyPublicIdentityUpdate(BaseModel):
    external_card_url: str = Field(min_length=1)
    title: str | None = None
    display_name: str | None = None


class PublicCardResponse(BaseModel):
    id: UUID
    display_name: str
    company_name: str
    title: str | None = None
    one_line_blurb: str | None = None
    avatar_url: str | None = None
    responsibility_keywords: list[str] = Field(default_factory=list)
    product_keywords: list[str] = Field(default_factory=list)
    external_card_url: str
    org_name: str


class StubListResponse(BaseModel):
    items: list[StubResponse]


class PublishResponse(BaseModel):
    status: str
    index_status: str = "indexing"


class CsvImportError(BaseModel):
    row: int
    reason: str


class CsvImportResponse(BaseModel):
    imported: int
    skipped: int
    errors: list[CsvImportError]
