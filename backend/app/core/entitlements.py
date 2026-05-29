from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserEntitlement


def _utc_today(d: datetime) -> datetime.date:
    if d.tzinfo is None:
        return d.date()
    return d.astimezone(UTC).date()


async def reset_search_cache_quota_if_needed(db: AsyncSession, ent: UserEntitlement) -> None:
    now = datetime.now(UTC)
    today = now.date()
    reset_at = ent.search_cache_reset_at

    if reset_at is None or _utc_today(reset_at) < today:
        ent.search_cache_used_today = 0
        ent.search_cache_reset_at = now
        await db.flush()
