from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ContactListItem(BaseModel):
    id: UUID
    display_name: str | None
    company_name: str | None
    title: str | None
    responsibility_scope: str | None
    responsibility_confidence: float | None
    source_label: str | None
    review_status: str
    image_url: str | None
    phones_preview: str | None = None
    emails_preview: str | None = None
    company_products_preview: str | None = None
    company_enrichment_status: str | None = None

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    items: list[ContactListItem]
    total: int


class ProvenanceField(BaseModel):
    name: str
    value: str | None
    source: str
    confidence: float | None


class CardOriginalSection(BaseModel):
    fields: list[ProvenanceField]
    image_url: str | None


class AiInferredSection(BaseModel):
    responsibility_scope: dict | None = None


class CompanyEnrichmentSection(BaseModel):
    status: str = "pending"
    main_products: list[str] | None = None
    website_url: str | None = None
    confidence: float | None = None
    provenance_label: str | None = None
    updated_at: str | None = None
    can_refresh: bool = False
    refresh_quota_remaining: int | None = None
    review_status: str | None = None
    needs_review: bool | None = None


class ContactSections(BaseModel):
    card_original: CardOriginalSection
    ai_inferred: AiInferredSection
    company_enrichment: CompanyEnrichmentSection


class ContactUpdateFields(BaseModel):
    display_name: str | None = None
    company_name: str | None = None
    title: str | None = None
    address: str | None = None
    website: str | None = None
    phone: str | None = None
    email: str | None = None


class ContactUpdateRequest(BaseModel):
    fields: ContactUpdateFields
    version: int


class ContactDetailResponse(BaseModel):
    id: UUID
    company_id: UUID | None = None
    display_name: str | None
    company_name: str | None
    title: str | None
    phones: list
    emails: list
    address: str | None
    website: str | None
    source_type: str | None
    source_label: str | None
    review_status: str
    image_url: str | None
    version: int
    sections: ContactSections
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
