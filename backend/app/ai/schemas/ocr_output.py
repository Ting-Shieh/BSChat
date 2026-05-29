from pydantic import BaseModel, Field


class OcrOutput(BaseModel):
    name: str | None = None
    company: str | None = None
    title: str | None = None
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    address: str | None = None
    website: str | None = None
    raw_text: str = ""
    field_confidences: dict[str, float] = Field(default_factory=dict)

    def to_extracted_fields(self) -> dict:
        return {
            "name": self.name,
            "company": self.company,
            "title": self.title,
            "phones": self.phones,
            "emails": self.emails,
            "address": self.address,
            "website": self.website,
        }

    def overall_confidence(self) -> float | None:
        review = ["name", "company", "title"]
        vals = [self.field_confidences.get(f, 0) for f in review if self.field_confidences.get(f) is not None]
        return sum(vals) / len(vals) if vals else None
