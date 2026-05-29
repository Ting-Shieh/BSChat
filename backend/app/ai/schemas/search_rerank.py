from pydantic import BaseModel, Field


class ParsedIntent(BaseModel):
    products: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    hard_roles: list[str] = Field(default_factory=list)
    hard_companies: list[str] = Field(default_factory=list)
    hard_products: list[str] = Field(default_factory=list)


class MatchSource(BaseModel):
    field: str
    value: str
    confidence: float | None = None


class RerankItem(BaseModel):
    contact_id: str
    match_score: float
    match_reason: str
    match_sources: list[MatchSource] = Field(default_factory=list)


class SearchRerankResponse(BaseModel):
    results: list[RerankItem] = Field(default_factory=list)
