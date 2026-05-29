from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    source_type: str | None = Field(default=None, examples=["event"])
    source_label: str | None = Field(default=None, examples=["Computex 2026"])


class UpdateSessionRequest(BaseModel):
    source_label: str | None = None
    status: str | None = Field(default=None, examples=["closed"])


class CaptureSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    workspace_id: UUID
    source_type: str | None
    source_label: str | None
    status: str
    card_count: int
    confirmed_count: int
    pending_count: int
    started_at: datetime
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class DuplicateWarning(BaseModel):
    previous_card_id: UUID
    scanned_at: datetime
    message: str


class RawCardUploadResponse(BaseModel):
    raw_card_id: UUID
    status: str
    capture_session_id: UUID | None
    duplicate_warning: DuplicateWarning | None = None


class OcrResultSummary(BaseModel):
    extracted_fields: dict
    field_confidences: dict
    overall_confidence: float | None = None
    engine: str | None = None
    engine_version: str | None = None

    model_config = {"from_attributes": True}


class CardListItem(BaseModel):
    id: UUID
    status: str
    review_status: str
    capture_method: str
    source_label: str | None
    image_url: str | None
    created_at: datetime
    ocr_summary: OcrResultSummary | None = None

    model_config = {"from_attributes": True}


class CardListResponse(BaseModel):
    items: list[CardListItem]


class CardDetailResponse(BaseModel):
    id: UUID
    capture_session_id: UUID | None
    status: str
    review_status: str
    version: int
    image_url: str | None
    capture_method: str
    source_type: str | None
    source_label: str | None
    created_at: datetime
    ocr_result: OcrResultSummary | None = None

    model_config = {"from_attributes": True}


class ReviewCardRequest(BaseModel):
    name: str | None = None
    company: str | None = None
    title: str | None = None
    version: int


class BatchUploadResponse(BaseModel):
    cards: list[RawCardUploadResponse]
