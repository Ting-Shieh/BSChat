import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="owner", uselist=False)
    entitlement: Mapped["UserEntitlement"] = relationship(back_populates="user", uselist=False)


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True
    )
    name: Mapped[str] = mapped_column(String(255), default="Personal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="workspace")


class UserEntitlement(Base):
    __tablename__ = "user_entitlements"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    plan_tier: Mapped[str] = mapped_column(String(10), default="free")
    auto_refresh_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_refresh_interval_days: Mapped[int] = mapped_column(Integer, default=90)
    manual_refresh_quota_monthly: Mapped[int] = mapped_column(Integer, default=3)
    manual_refresh_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    search_cache_daily_quota: Mapped[int] = mapped_column(Integer, default=30)
    search_cache_used_today: Mapped[int] = mapped_column(Integer, default=0)
    search_cache_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live_augment_monthly_quota: Mapped[int] = mapped_column(Integer, default=5)
    live_augment_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    daily_enrich_quota: Mapped[int] = mapped_column(Integer, default=50)
    daily_enrich_used: Mapped[int] = mapped_column(Integer, default=0)
    daily_enrich_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manual_refresh_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # M3.5 person enrichment (Pro)
    person_enrich_mode: Mapped[str] = mapped_column(String(20), default="inference_only")
    person_linkedin_quota_monthly: Mapped[int] = mapped_column(Integer, default=0)
    person_linkedin_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    person_linkedin_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    person_linkedin_auto_on_url: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="entitlement")
