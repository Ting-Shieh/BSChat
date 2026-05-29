from pydantic import BaseModel, Field


class EnrichOutput(BaseModel):
    main_products: list[str] = Field(default_factory=list)
    summary: str | None = None
    industry_tags: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.0
    fields_provenance: dict = Field(default_factory=dict)
