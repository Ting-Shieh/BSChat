import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class EnterpriseApplication(Base):
    __tablename__ = "enterprise_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    company_name: Mapped[str] = mapped_column(String(255))
    slug_requested: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255))
    estimated_seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resulting_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
