from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import create_access_token
from app.core.entitlements import apply_plan_preset
from app.core.db import get_db
from app.models.user import User, UserEntitlement, Workspace
from app.schemas.auth import DevLoginRequest, TokenResponse

router = APIRouter()

_ALLOWED_PLAN_TIERS = frozenset({"free", "pro", "enterprise"})


@router.post("/dev-login", response_model=TokenResponse, summary="M1 dev login (MVP only)")
async def dev_login(body: DevLoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Create or fetch dev user and return JWT. Disable in production."""
    plan_tier = (body.plan_tier or "free").lower()
    if plan_tier not in _ALLOWED_PLAN_TIERS:
        raise HTTPException(status_code=400, detail="UNKNOWN_PLAN_TIER")

    result = await db.execute(
        select(User).where(User.email == body.email).options(selectinload(User.entitlement))
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(email=body.email, display_name=body.display_name)
        db.add(user)
        await db.flush()
        workspace = Workspace(owner_user_id=user.id, name="Personal")
        entitlement = UserEntitlement(user_id=user.id)
        apply_plan_preset(entitlement, plan_tier)
        db.add(workspace)
        db.add(entitlement)
    else:
        if body.display_name:
            user.display_name = body.display_name
        entitlement = user.entitlement
        if entitlement is None:
            entitlement = UserEntitlement(user_id=user.id)
            db.add(entitlement)
        apply_plan_preset(entitlement, plan_tier)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)
