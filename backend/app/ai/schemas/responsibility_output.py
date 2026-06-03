from pydantic import BaseModel, Field


class ResponsibilityOutput(BaseModel):
    scope: str = Field(description="可能負責… 1-2 句繁中")
    confidence: float = Field(ge=0.0, le=1.0)
