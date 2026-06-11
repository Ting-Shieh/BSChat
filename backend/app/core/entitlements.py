from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserEntitlement

# Pilot TBD values (PRD §11.2.1). Applied on plan switch; quotas reset on tier change.
PLAN_PRESETS: dict[str, dict] = {
    "free": {
        "person_enrich_mode": "inference_only",
        "person_linkedin_quota_monthly": 0,
        "person_linkedin_auto_on_url": False,
        "auto_refresh_enabled": False,
        "auto_refresh_interval_days": 90,
        "manual_refresh_quota_monthly": 3,
        "search_cache_daily_quota": 30,
        "live_augment_monthly_quota": 5,
    },
    "pro": {
        "person_enrich_mode": "linkedin_llm",
        "person_linkedin_quota_monthly": 20,
        "person_linkedin_auto_on_url": True,
        "auto_refresh_enabled": True,
        "auto_refresh_interval_days": 90,
        "manual_refresh_quota_monthly": 50,
        "search_cache_daily_quota": 50,
        "live_augment_monthly_quota": 30,
    },
    "enterprise": {
        "person_enrich_mode": "linkedin_llm",
        "person_linkedin_quota_monthly": 100,
        "person_linkedin_auto_on_url": True,
        "auto_refresh_enabled": True,
        "auto_refresh_interval_days": 90,
        "manual_refresh_quota_monthly": 100,
        "search_cache_daily_quota": 100,
        "live_augment_monthly_quota": 100,
    },
}


def apply_plan_preset(ent: UserEntitlement, plan_tier: str) -> None:
    """Set plan_tier and apply its quota/feature preset.

    On downgrade to free, Pro features (auto-refresh, LinkedIn) are turned off but
    existing cached data is preserved (DDR — M6 §exceptions).
    """
    preset = PLAN_PRESETS.get(plan_tier)
    if preset is None:
        raise HTTPException(status_code=400, detail="UNKNOWN_PLAN_TIER")
    ent.plan_tier = plan_tier
    for key, value in preset.items():
        setattr(ent, key, value)


def is_person_enrich_allowed(ent: UserEntitlement | None) -> bool:
    return bool(ent and ent.person_enrich_mode == "linkedin_llm")


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


async def reset_person_linkedin_quota_if_needed(db: AsyncSession, ent: UserEntitlement) -> None:
    now = datetime.now(UTC)
    reset_at = ent.person_linkedin_reset_at
    if reset_at is None or not _same_calendar_month(reset_at, now):
        ent.person_linkedin_used_this_month = 0
        ent.person_linkedin_reset_at = now
        await db.flush()


def person_linkedin_remaining(ent: UserEntitlement) -> int:
    """Remaining person enrichments this month; -1 = unlimited."""
    quota = ent.person_linkedin_quota_monthly
    if quota < 0:
        return -1
    return max(0, quota - ent.person_linkedin_used_this_month)


async def consume_person_linkedin_quota(db: AsyncSession, ent: UserEntitlement) -> int:
    """Increment person-enrich usage; returns remaining (-1 = unlimited).

    Raises 403 if the plan does not allow person enrich, 429 if quota exhausted.
    """
    if not is_person_enrich_allowed(ent):
        raise HTTPException(status_code=403, detail="PERSON_ENRICH_NOT_ALLOWED")
    await reset_person_linkedin_quota_if_needed(db, ent)
    quota = ent.person_linkedin_quota_monthly
    if quota < 0:
        return -1
    if ent.person_linkedin_used_this_month >= quota:
        raise HTTPException(status_code=429, detail="PERSON_LINKEDIN_QUOTA_EXCEEDED")
    ent.person_linkedin_used_this_month += 1
    await db.flush()
    return quota - ent.person_linkedin_used_this_month
