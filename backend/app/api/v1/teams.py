from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.modules.team_invite import service as invite_service
from app.schemas.team import (
    CreateInviteRequest,
    CreateInviteResponse,
    CreateTeamRequest,
    InvitePreviewResponse,
    TeamResponse,
)

router = APIRouter(tags=["teams"])


@router.post("/teams", response_model=TeamResponse)
async def create_team(
    body: CreateTeamRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    org = await invite_service.create_team(db, user, name=body.name, slug=body.slug)
    await db.commit()
    return TeamResponse(org_id=org.id, org_name=org.name, slug=org.slug)


@router.post("/invites", response_model=CreateInviteResponse)
async def create_invite(
    body: CreateInviteRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CreateInviteResponse:
    invite, raw = await invite_service.create_invite(
        db,
        user,
        org_id=body.org_id,
        expires_days=body.expires_days,
        max_uses=body.max_uses,
    )
    org = await invite_service.require_org_member(db, user.id, body.org_id)
    await db.commit()
    return CreateInviteResponse(
        invite_id=invite.id,
        token=raw,
        org_id=org.id,
        org_name=org.name,
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        join_path=f"/join/{raw}",
    )


@router.get("/invites/{token}", response_model=InvitePreviewResponse)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)) -> InvitePreviewResponse:
    invite, org = await invite_service.preview_invite(db, token)
    return InvitePreviewResponse(
        org_id=org.id,
        org_name=org.name,
        slug=org.slug,
        expires_at=invite.expires_at,
        seats_remaining=max(0, invite.max_uses - invite.use_count),
    )


@router.post("/invites/{token}/accept", response_model=TeamResponse)
async def accept_invite(
    token: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    org = await invite_service.accept_invite(db, user, token)
    await db.commit()
    return TeamResponse(org_id=org.id, org_name=org.name, slug=org.slug)


@router.post("/invites/{invite_id}/revoke", status_code=204)
async def revoke_invite(
    invite_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await invite_service.revoke_invite(db, user, invite_id)
    await db.commit()
