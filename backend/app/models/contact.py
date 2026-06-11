import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id"))
    raw_card_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsibility_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsibility_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    phones: Mapped[list] = mapped_column(JSONB, default=list)
    emails: Mapped[list] = mapped_column(JSONB, default=list)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capture_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="unconfirmed")
    search_status: Mapped[str] = mapped_column(String(20), default="indexed")
    search_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    # M3.5 person enrichment (Pro)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    person_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    person_scope_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    person_enrich_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    person_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    provenance: Mapped[list["ContactFieldProvenance"]] = relationship(back_populates="contact")


class ContactFieldProvenance(Base):
    __tablename__ = "contact_field_provenance"
    __table_args__ = (UniqueConstraint("contact_id", "field_name", name="uq_contact_field"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), index=True)
    field_name: Mapped[str] = mapped_column(String(50))
    current_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="ocr")
    source_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contact: Mapped[Contact] = relationship(back_populates="provenance")
