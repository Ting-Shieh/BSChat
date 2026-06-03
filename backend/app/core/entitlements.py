from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserEntitlement


def _utc_today(d: datetime) -> datetime.date:
    if d.tzinfo is None:
        return d.date()
    return d.astimezone(UTC).date()


def _same_calendar_month(a: datetime, b: datetime) -> bool:
    return a.year == b.year and a.month == b.month


async def reset_search_cache_quota_if_needed(db: AsyncSession, ent: UserEntitlement) -> None:
    now = datetime.now(UTC)
    today = now.date()
    reset_at = ent.search_cache_reset_at

    if reset_at is None or _utc_today(reset_at) < today:
        ent.search_cache_used_today = 0
        ent.search_cache_reset_at = now
        await db.flush()


async def reset_manual_refresh_quota_if_needed(db: AsyncSession, ent: UserEntitlement) -> None:
    now = datetime.now(UTC)
    reset_at = ent.manual_refresh_reset_at
    if reset_at is None or not _same_calendar_month(reset_at, now):
        ent.manual_refresh_used_this_month = 0
        ent.manual_refresh_reset_at = now
        await db.flush()


def manual_refresh_remaining(ent: UserEntitlement) -> int:
    """Remaining manual refreshes this month; -1 = unlimited (Pro pilot)."""
    quota = ent.manual_refresh_quota_monthly
    if quota < 0:
        return -1
    return max(0, quota - ent.manual_refresh_used_this_month)


async def consume_manual_refresh_quota(db: AsyncSession, ent: UserEntitlement) -> int:
    """Increment usage; returns remaining (-1 = unlimited)."""
    await reset_manual_refresh_quota_if_needed(db, ent)
    quota = ent.manual_refresh_quota_monthly
    if quota < 0:
        return -1
    if ent.manual_refresh_used_this_month >= quota:
        raise HTTPException(status_code=429, detail="MANUAL_REFRESH_QUOTA_EXCEEDED")
    ent.manual_refresh_used_this_month += 1
    await db.flush()
    return quota - ent.manual_refresh_used_this_month
