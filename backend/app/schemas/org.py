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
    external_card_url: str


class StubUpdateRequest(BaseModel):
    display_name: str | None = None
    company_name: str | None = None
    title: str | None = None
    responsibility_keywords: list[str] | None = None
    product_keywords: list[str] | None = None
    external_card_url: str | None = None


class StubResponse(BaseModel):
    id: UUID
    org_id: UUID
    display_name: str
    company_name: str
    title: str | None
    responsibility_keywords: list[str]
    product_keywords: list[str]
    external_card_url: str
    status: str
    published_at: datetime | None
    unpublished_at: datetime | None
    created_at: datetime
    updated_at: datetime


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
