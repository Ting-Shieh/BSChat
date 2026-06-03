from pydantic import BaseModel, Field


class WebsiteCandidate(BaseModel):
    url: str
    confidence: float = Field(ge=0.0, le=1.0)


class WebsiteDiscoveryOutput(BaseModel):
    candidates: list[WebsiteCandidate] = Field(default_factory=list)
