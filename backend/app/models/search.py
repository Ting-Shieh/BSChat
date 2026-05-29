import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    query_text: Mapped[str] = mapped_column(Text)
    parsed_intent: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    search_scope: Mapped[str] = mapped_column(String(20), default="private")
    retrieval_mode: Mapped[str] = mapped_column(String(20), default="cache")
    live_augmentation_used: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    suggest_live: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SearchResult(Base):
    __tablename__ = "search_results"
    __table_args__ = (UniqueConstraint("query_id", "contact_id", name="uq_search_result_contact"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_queries.id", ondelete="CASCADE"), index=True
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    rank: Mapped[int] = mapped_column(Integer)
    match_score: Mapped[float] = mapped_column(Float)
    match_reason: Mapped[str] = mapped_column(Text)
    match_sources: Mapped[list] = mapped_column(JSONB, default=list)
    live_products: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    source_pool: Mapped[str] = mapped_column(String(30), default="private_rolodex")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
