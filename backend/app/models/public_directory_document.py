import hashlib
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PublicDirectoryDocument(Base):
    __tablename__ = "public_directory_documents"

    stub_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("public_business_stubs.id", ondelete="CASCADE"), primary_key=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    search_text: Mapped[str] = mapped_column(Text)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def content_hash_for(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
