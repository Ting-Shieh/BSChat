from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.core.entitlements import (
    apply_plan_preset,
    manual_refresh_remaining,
    person_linkedin_remaining,
    reset_live_augment_quota_if_needed,
    reset_manual_refresh_quota_if_needed,
    reset_person_linkedin_quota_if_needed,
    reset_search_cache_quota_if_needed,
)
from app.models.user import UserEntitlement
from app.schemas.auth import (
    AutoRefreshInfo,
    MeResponse,
    PersonEnrichInfo,
    PlanSwitchRequest,
    QuotaInfo,
    SettingsUpdateRequest,
)

router = APIRouter()

ALLOWED_REFRESH_INTERVALS = {30, 60, 90}


def _build_me(user, entitlement: UserEntitlement) -> MeResponse:
    manual_remaining = manual_refresh_remaining(entitlement)
    if manual_remaining < 0:
        manual_remaining = 999
    person_remaining = person_linkedin_remaining(entitlement)
    if person_remaining < 0:
        person_remaining = 999

    return MeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        workspace_id=user.workspace.id,
        plan_tier=entitlement.plan_tier,
        quotas=QuotaInfo(
            search_cache_remaining_today=max(
                0, entitlement.search_cache_daily_quota - entitlement.search_cache_used_today
            ),
            live_augment_remaining_month=max(
                0, entitlement.live_augment_monthly_quota - entitlement.live_augment_used_this_month
            ),
            manual_refresh_remaining_month=manual_remaining,
            person_linkedin_remaining_month=person_remaining,
        ),
        person_enrich=PersonEnrichInfo(
            mode=entitlement.person_enrich_mode,
            auto_on_url=entitlement.person_linkedin_auto_on_url,
        ),
        auto_refresh=AutoRefreshInfo(
            enabled=entitlement.auto_refresh_enabled,
            interval_days=entitlement.auto_refresh_interval_days,
        ),
    )


@router.get("", response_model=MeResponse, summary="Current user + entitlements")
async def get_me(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    entitlement = user.entitlement
    await reset_search_cache_quota_if_needed(db, entitlement)
    await reset_manual_refresh_quota_if_needed(db, entitlement)
    await reset_person_linkedin_quota_if_needed(db, entitlement)
    await reset_live_augment_quota_if_needed(db, entitlement)
    await db.flush()
    return _build_me(user, entitlement)


@router.post("/plan", response_model=MeResponse, summary="Switch plan tier (dev/MVP, no billing)")
async def switch_plan(
    body: PlanSwitchRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    """MVP plan switch without real billing — applies the tier quota preset."""
    apply_plan_preset(user.entitlement, body.plan_tier)
    await db.commit()
    await db.refresh(user.entitlement)
    return _build_me(user, user.entitlement)


@router.patch("/settings", response_model=MeResponse, summary="Update Pro settings")
async def update_settings(
    body: SettingsUpdateRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    ent = user.entitlement
    is_pro = ent.person_enrich_mode == "linkedin_llm"

    if body.auto_refresh_interval_days is not None:
        if body.auto_refresh_interval_days not in ALLOWED_REFRESH_INTERVALS:
            raise HTTPException(status_code=400, detail="INVALID_REFRESH_INTERVAL")
        ent.auto_refresh_interval_days = body.auto_refresh_interval_days

    if body.auto_refresh_enabled is not None:
        if body.auto_refresh_enabled and not is_pro:
            raise HTTPException(status_code=403, detail="PRO_REQUIRED")
        ent.auto_refresh_enabled = body.auto_refresh_enabled

    if body.person_linkedin_auto_on_url is not None:
        if body.person_linkedin_auto_on_url and not is_pro:
            raise HTTPException(status_code=403, detail="PRO_REQUIRED")
        ent.person_linkedin_auto_on_url = body.person_linkedin_auto_on_url

    await db.commit()
    await db.refresh(ent)
    return _build_me(user, ent)
