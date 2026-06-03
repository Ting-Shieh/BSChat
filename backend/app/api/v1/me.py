from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.core.entitlements import (
    manual_refresh_remaining,
    reset_manual_refresh_quota_if_needed,
    reset_search_cache_quota_if_needed,
)
from app.schemas.auth import MeResponse, QuotaInfo

router = APIRouter()


@router.get("", response_model=MeResponse, summary="Current user + entitlements")
async def get_me(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    entitlement = user.entitlement
    workspace = user.workspace
    await reset_search_cache_quota_if_needed(db, entitlement)
    await reset_manual_refresh_quota_if_needed(db, entitlement)
    await db.flush()

    manual_remaining = manual_refresh_remaining(entitlement)
    if manual_remaining < 0:
        manual_remaining = 999

    return MeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        workspace_id=workspace.id,
        plan_tier=entitlement.plan_tier,
        quotas=QuotaInfo(
            search_cache_remaining_today=max(
                0, entitlement.search_cache_daily_quota - entitlement.search_cache_used_today
            ),
            live_augment_remaining_month=max(
                0, entitlement.live_augment_monthly_quota - entitlement.live_augment_used_this_month
            ),
            manual_refresh_remaining_month=manual_remaining,
        ),
    )
