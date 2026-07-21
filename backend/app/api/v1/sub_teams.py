from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.modules.sub_team import service as sub_team_service
from app.schemas.sub_team import (
    CreateSubTeamInviteRequest,
    CreateSubTeamInviteResponse,
    CreateSubTeamRequest,
    OrgSubTeamAdminRow,
    SubTeamDetail,
    SubTeamInvitePreview,
    SubTeamMemberInfo,
    SubTeamSummary,
)

router = APIRouter(tags=["sub-teams"])


@router.get("/sub-teams", response_model=list[SubTeamSummary])
async def list_sub_teams(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[SubTeamSummary]:
    rows = await sub_team_service.list_my_sub_teams(db, user)
    return [
        SubTeamSummary(
            id=team.id,
            org_id=team.org_id,
            name=team.name,
            description=team.description,
            role=role,
            member_count=count,
        )
        for team, role, count in rows
    ]


@router.post("/sub-teams", response_model=SubTeamSummary, status_code=201)
async def create_sub_team(
    body: CreateSubTeamRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SubTeamSummary:
    team = await sub_team_service.create_sub_team(
        db, user, name=body.name, description=body.description
    )
    await db.commit()
    return SubTeamSummary(
        id=team.id,
        org_id=team.org_id,
        name=team.name,
        description=team.description,
        role="owner",
        member_count=1,
    )


@router.get("/sub-teams/{team_id}", response_model=SubTeamDetail)
async def get_sub_team(
    team_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SubTeamDetail:
    team, org, membership = await sub_team_service.require_sub_team_access(db, user.id, team_id)
    members = await sub_team_service.list_members(db, team_id)
    return SubTeamDetail(
        id=team.id,
        org_id=team.org_id,
        org_name=org.name,
        name=team.name,
        description=team.description,
        my_role=membership.role if membership else None,
        member_count=len(members),
        members=[
            SubTeamMemberInfo(
                user_id=u.id,
                display_name=u.display_name,
                email=u.email,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m, u in members
        ],
    )


@router.post("/sub-teams/{team_id}/invites", response_model=CreateSubTeamInviteResponse)
async def create_sub_team_invite(
    team_id: UUID,
    body: CreateSubTeamInviteRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CreateSubTeamInviteResponse:
    invite, raw, team = await sub_team_service.create_sub_team_invite(
        db,
        user,
        team_id=team_id,
        expires_days=body.expires_days,
        max_uses=body.max_uses,
    )
    _, org, _ = await sub_team_service.require_sub_team_access(db, user.id, team_id)
    await db.commit()
    return CreateSubTeamInviteResponse(
        invite_id=invite.id,
        token=raw,
        sub_team_id=team.id,
        sub_team_name=team.name,
        org_name=org.name,
        expires_at=invite.expires_at,
        join_path=f"/join/team/{raw}",
    )


@router.get("/join/sub-team/{token}", response_model=SubTeamInvitePreview)
async def preview_sub_team_invite(
    token: str, db: AsyncSession = Depends(get_db)
) -> SubTeamInvitePreview:
    invite, team, org = await sub_team_service.preview_sub_team_invite(db, token)
    return SubTeamInvitePreview(
        sub_team_id=team.id,
        sub_team_name=team.name,
        org_id=org.id,
        org_name=org.name,
        expires_at=invite.expires_at,
        seats_remaining=max(0, invite.max_uses - invite.use_count),
    )


@router.post("/join/sub-team/{token}", response_model=SubTeamSummary)
async def accept_sub_team_invite(
    token: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SubTeamSummary:
    team = await sub_team_service.accept_sub_team_invite(db, user, token)
    await db.commit()
    rows = await sub_team_service.list_my_sub_teams(db, user)
    for t, role, count in rows:
        if t.id == team.id:
            return SubTeamSummary(
                id=t.id,
                org_id=t.org_id,
                name=t.name,
                description=t.description,
                role=role,
                member_count=count,
            )
    return SubTeamSummary(
        id=team.id,
        org_id=team.org_id,
        name=team.name,
        description=team.description,
        role="member",
        member_count=1,
    )


@router.delete("/sub-teams/{team_id}/members/{user_id}", status_code=204)
async def remove_sub_team_member(
    team_id: UUID,
    user_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await sub_team_service.remove_member(db, user, team_id=team_id, target_user_id=user_id)
    await db.commit()


@router.post("/sub-teams/{team_id}/leave", status_code=204)
async def leave_sub_team(
    team_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await sub_team_service.leave_sub_team(db, user, team_id)
    await db.commit()


@router.delete("/sub-teams/{team_id}", status_code=204)
async def dissolve_sub_team(
    team_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await sub_team_service.dissolve_sub_team(db, user, team_id)
    await db.commit()


@router.get("/orgs/{org_id}/sub-teams", response_model=list[OrgSubTeamAdminRow])
async def admin_list_sub_teams(
    org_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[OrgSubTeamAdminRow]:
    rows = await sub_team_service.list_org_sub_teams(db, user, org_id)
    return [
        OrgSubTeamAdminRow(
            id=team.id,
            name=team.name,
            member_count=count,
            owner_label=owner,
            created_at=team.created_at,
        )
        for team, count, owner in rows
    ]
