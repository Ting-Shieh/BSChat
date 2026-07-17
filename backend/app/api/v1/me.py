from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.core.entitlements import (
    apply_plan_preset,
    manual_refresh_remaining,
    person_linkedin_remaining,
    public_recommend_unlimited,
    remaining_public_recommend,
    reset_live_augment_quota_if_needed,
    reset_manual_refresh_quota_if_needed,
    reset_person_linkedin_quota_if_needed,
    reset_search_cache_quota_if_needed,
)
from app.models.user import UserEntitlement
from app.schemas.auth import (
    AutoRefreshInfo,
    MeResponse,
    OrgMembershipInfo,
    PersonEnrichInfo,
    PlanSwitchRequest,
    QuotaInfo,
    SearchPrecisionInfo,
    SettingsUpdateRequest,
)
from app.modules.m11_public_directory.service import list_user_org_memberships
from app.modules.m5_search.precision import can_use_exploratory, normalize_precision, validate_precision_update

router = APIRouter()

ALLOWED_REFRESH_INTERVALS = {30, 60, 90}


def _org_infos(memberships: list, user_id) -> list[OrgMembershipInfo]:
    infos: list[OrgMembershipInfo] = []
    for org, role in memberships:
        is_ent = bool(getattr(org, "is_enterprise", False))
        infos.append(
            OrgMembershipInfo(
                org_id=org.id,
                org_name=org.name,
                role=role,
                is_enterprise=is_ent,
                is_primary_admin=is_ent and org.primary_admin_user_id == user_id,
            )
        )
    return infos


def _build_me(user, entitlement: UserEntitlement, org_memberships: list[OrgMembershipInfo]) -> MeResponse:
    manual_remaining = manual_refresh_remaining(entitlement)
    if manual_remaining < 0:
        manual_remaining = 999
    person_remaining = person_linkedin_remaining(entitlement)
    if person_remaining < 0:
        person_remaining = 999
    unlimited = public_recommend_unlimited(entitlement)
    public_remaining = remaining_public_recommend(entitlement)

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
            public_recommend_remaining_lifetime=0 if unlimited else public_remaining,
            public_recommend_unlimited=unlimited,
        ),
        person_enrich=PersonEnrichInfo(
            mode=entitlement.person_enrich_mode,
            auto_on_url=entitlement.person_linkedin_auto_on_url,
        ),
        auto_refresh=AutoRefreshInfo(
            enabled=entitlement.auto_refresh_enabled,
            interval_days=entitlement.auto_refresh_interval_days,
        ),
        search_precision=SearchPrecisionInfo(
            mode=normalize_precision(getattr(entitlement, "search_precision", None)),
            can_use_exploratory=can_use_exploratory(entitlement.plan_tier),
        ),
        org_memberships=org_memberships,
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
    memberships = await list_user_org_memberships(db, user.id)
    org_info = _org_infos(memberships, user.id)
    return _build_me(user, entitlement, org_info)


@router.post("/plan", response_model=MeResponse, summary="Switch plan tier (dev only)")
async def switch_plan(
    body: PlanSwitchRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MeResponse:
    """Dev/test only — gated by ALLOW_DEV_LOGIN. Product UI must not call this."""
    from app.core.config import get_settings

    if not get_settings().allow_dev_login:
        raise HTTPException(status_code=403, detail="DEV_LOGIN_DISABLED")
    apply_plan_preset(user.entitlement, body.plan_tier)
    await db.commit()
    await db.refresh(user.entitlement)
    memberships = await list_user_org_memberships(db, user.id)
    org_info = _org_infos(memberships, user.id)
    return _build_me(user, user.entitlement, org_info)


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

    if body.search_precision is not None:
        try:
            ent.search_precision = validate_precision_update(ent.plan_tier, body.search_precision)
        except ValueError:
            raise HTTPException(status_code=403, detail="SEARCH_PRECISION_NOT_ALLOWED")

    await db.commit()
    await db.refresh(ent)
    memberships = await list_user_org_memberships(db, user.id)
    org_info = _org_infos(memberships, user.id)
    return _build_me(user, ent, org_info)
