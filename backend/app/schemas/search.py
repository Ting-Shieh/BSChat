from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSearchQueryRequest(BaseModel):
    query_text: str = Field(min_length=1, max_length=2000)
    search_scope: str = "private"
    session_id: UUID | None = None


class MatchSourceDTO(BaseModel):
    field: str
    value: str
    confidence: float | None = None


class ContactPreviewDTO(BaseModel):
    display_name: str | None
    company_name: str | None
    title: str | None
    review_status: str
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    image_url: str | None = None


class SearchResultItemDTO(BaseModel):
    contact_id: UUID
    rank: int
    match_score: float
    match_reason: str
    match_sources: list[MatchSourceDTO]
    source_pool: str = "private_rolodex"
    contact_preview: ContactPreviewDTO


class SearchEmptyStateDTO(BaseModel):
    reason: str
    suggestions: list[str] = Field(default_factory=list)
    sample_queries: list[str] = Field(default_factory=list)
    cta: dict | None = None


class SearchQuotasDTO(BaseModel):
    search_cache_remaining_today: int
    live_augment_remaining_month: int


class SearchStatusResponse(BaseModel):
    indexed_count: int
    can_search: bool
    min_recommended: int = 3
    sample_queries: list[str]
    quotas: SearchQuotasDTO


class SearchQueryResponse(BaseModel):
    query_id: UUID
    status: str
    result_count: int = 0
    latency_ms: int | None = None
    degraded: bool = False
    aha_moment: bool = False
    suggest_live: bool = False
    results: list[SearchResultItemDTO] = Field(default_factory=list)
    empty_state: SearchEmptyStateDTO | None = None
