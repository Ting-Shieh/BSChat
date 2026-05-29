import uuid
from typing import Any

from pydantic import BaseModel, Field


class ContactUpsertFields(BaseModel):
    name: str | None = None
    company: str | None = None
    title: str | None = None
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    address: str | None = None
    website: str | None = None


class ContactUpsertRequested(BaseModel):
    eventId: str
    userId: str
    workspaceId: str
    rawCardId: str
    fields: ContactUpsertFields | dict[str, Any]
    fieldConfidences: dict[str, float] = Field(default_factory=dict)
    provenance: dict[str, str] = Field(default_factory=dict)
    sourceType: str | None = None
    sourceLabel: str | None = None
    captureMethod: str | None = None
    imageUrl: str | None = None
    reviewStatus: str = "auto_accepted"
    occurredAt: str | None = None

    def parsed_fields(self) -> ContactUpsertFields:
        if isinstance(self.fields, ContactUpsertFields):
            return self.fields
        return ContactUpsertFields.model_validate(self.fields)
