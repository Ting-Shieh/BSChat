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


class StubPreviewDTO(BaseModel):
    display_name: str
    company_name: str
    title: str | None = None
    product_keywords: list[str] = Field(default_factory=list)


class SearchResultItemDTO(BaseModel):
    rank: int
    match_score: float
    match_reason: str
    match_sources: list[MatchSourceDTO]
    source_pool: str = "private_rolodex"
    contact_id: UUID | None = None
    contact_preview: ContactPreviewDTO | None = None
    stub_id: UUID | None = None
    stub_preview: StubPreviewDTO | None = None
    publisher_org_id: UUID | None = None
    publisher_org_name: str | None = None
    external_card_url: str | None = None
    live_products: list[str] | None = None
    opening_line: str | None = None
    collaboration_note: str | None = None
    dormant_months: int | None = None


class LiveAugmentRequest(BaseModel):
    contact_ids: list[UUID] | None = None


class SearchEmptyStateDTO(BaseModel):
    reason: str
    suggestions: list[str] = Field(default_factory=list)
    sample_queries: list[str] = Field(default_factory=list)
    cta: dict | None = None
    search_precision: str | None = None
    precision_hint: str | None = None


class RetrievalCandidateDebugDTO(BaseModel):
    id: str
    label: str
    retrieval_score: float


class PoolRetrievalDebugDTO(BaseModel):
    pool: str
    lexical_query: str
    semantic_query: str
    ts_hits: int
    trgm_extra_hits: int
    vector_hits: int
    widened: bool
    top_candidates: list[RetrievalCandidateDebugDTO] = Field(default_factory=list)


class SearchDebugDTO(BaseModel):
    search_scope: str
    search_precision: str
    intent_prompt_version: str
    rerank_prompt_version: str
    semantic_query: str
    parsed_intent: dict
    private: PoolRetrievalDebugDTO | None = None
    public: PoolRetrievalDebugDTO | None = None
    rerank_input_count: int
    result_count: int
    degraded: bool
    latency_ms: int | None = None


class SearchQuotasDTO(BaseModel):
    search_cache_remaining_today: int
    live_augment_remaining_month: int


class SearchStatusResponse(BaseModel):
    indexed_count: int
    can_search: bool
    min_recommended: int = 3
    sample_queries: list[str]
    quotas: SearchQuotasDTO
    public_pool_count: int = 0


class BriefingDTO(BaseModel):
    """Opportunity-briefing headline synthesised over the private rolodex."""

    headline: str
    scanned_count: int
    match_count: int
    dormant_count: int


class SearchQueryResponse(BaseModel):
    query_id: UUID
    status: str
    result_count: int = 0
    latency_ms: int | None = None
    degraded: bool = False
    aha_moment: bool = False
    suggest_live: bool = False
    results: list[SearchResultItemDTO] = Field(default_factory=list)
    briefing: BriefingDTO | None = None
    empty_state: SearchEmptyStateDTO | None = None
    debug: SearchDebugDTO | None = None
