from fastapi import APIRouter

from app.core.auth import CurrentUser
from app.schemas.auth import MeResponse, QuotaInfo

router = APIRouter()


@router.get("", response_model=MeResponse, summary="Current user + entitlements")
async def get_me(user: CurrentUser) -> MeResponse:
    entitlement = user.entitlement
    workspace = user.workspace
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
            manual_refresh_remaining_month=max(
                0, entitlement.manual_refresh_quota_monthly - entitlement.manual_refresh_used_this_month
            ),
        ),
    )
