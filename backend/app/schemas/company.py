from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.contact import CompanyEnrichmentSection


class ReEnrichResponse(BaseModel):
    status: str = "queued"
    manual_refresh_remaining_month: int


class CompanyDetailResponse(BaseModel):
    id: UUID
    display_name: str
    website_url: str | None
    enrich_status: str
    last_enriched_at: datetime | None
    enrichment: CompanyEnrichmentSection
    latest_enrichment_version: int
