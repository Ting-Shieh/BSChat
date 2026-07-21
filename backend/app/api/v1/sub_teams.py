import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.db import get_db
from app.modules.notifications import service as notif_service
from app.modules.sub_team import service as sub_team_service
from app.modules.sub_team.email import send_sub_team_invite_email
from app.schemas.sub_team import (
    CreateSubTeamInviteRequest,
    CreateSubTeamInviteResponse,
    CreateSubTeamRequest,
    NotificationItem,
    NotificationListResponse,
    OrgSubTeamAdminRow,
    SubTeamDetail,
    SubTeamInviteListItem,
    SubTeamInvitePreview,
    SubTeamMemberInfo,
    SubTeamSummary,
)

logger = logging.getLogger(__name__)
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
    invite, raw, team, org, _invitee = await sub_team_service.create_sub_team_invite(
        db,
        user,
        team_id=team_id,
        invited_email=str(body.email),
        expires_days=body.expires_days,
    )
    await db.commit()
    join_path = f"/join/team/{raw}"
    join_url = f"{get_settings().frontend_base_url.rstrip('/')}{join_path}"
    email_sent = False
    try:
        email_sent = await send_sub_team_invite_email(
            to_email=invite.invited_email or str(body.email),
            org_name=org.name,
            team_name=team.name,
            inviter_name=user.display_name or user.email,
            join_url=join_url,
            expires_at=invite.expires_at,
        )
    except HTTPException as exc:
        logger.warning("Sub-team invite email failed: %s", exc.detail)
        email_sent = False
    except Exception as exc:
        logger.warning("Sub-team invite email failed: %s", exc)
        email_sent = False
    return CreateSubTeamInviteResponse(
        invite_id=invite.id,
        token=raw,
        sub_team_id=team.id,
        sub_team_name=team.name,
        org_name=org.name,
        invited_email=invite.invited_email or str(body.email),
        expires_at=invite.expires_at,
        join_path=join_path,
        email_sent=email_sent,
    )


@router.get("/sub-teams/{team_id}/invites", response_model=list[SubTeamInviteListItem])
async def list_sub_team_invites(
    team_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[SubTeamInviteListItem]:
    invites = await sub_team_service.list_sub_team_invites(db, user, team_id)
    return [
        SubTeamInviteListItem(
            invite_id=i.id,
            invited_email=i.invited_email,
            status=sub_team_service.invite_status(i),  # type: ignore[arg-type]
            expires_at=i.expires_at,
            created_at=i.created_at,
            revoked_at=i.revoked_at,
            use_count=i.use_count,
            max_uses=i.max_uses,
        )
        for i in invites
    ]


@router.post("/sub-teams/invites/{invite_id}/revoke", status_code=204)
async def revoke_sub_team_invite(
    invite_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await sub_team_service.revoke_sub_team_invite(db, user, invite_id)
    await db.commit()


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
        invited_email=invite.invited_email,
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


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    items = await notif_service.list_my_notifications(db, user, unread_only=unread_only)
    unread = await notif_service.unread_count(db, user)
    return NotificationListResponse(
        items=[
            NotificationItem(
                id=n.id,
                kind=n.kind,
                title=n.title,
                body=n.body,
                payload=n.payload or {},
                read_at=n.read_at,
                created_at=n.created_at,
            )
            for n in items
        ],
        unread_count=unread,
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationItem)
async def mark_notification_read(
    notification_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> NotificationItem:
    n = await notif_service.mark_read(db, user, notification_id)
    await db.commit()
    return NotificationItem(
        id=n.id,
        kind=n.kind,
        title=n.title,
        body=n.body,
        payload=n.payload or {},
        read_at=n.read_at,
        created_at=n.created_at,
    )


@router.post("/notifications/{notification_id}/accept", response_model=SubTeamSummary)
async def accept_notification(
    notification_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SubTeamSummary:
    n = await notif_service.get_owned_notification(db, user, notification_id)
    if n.kind != "sub_team_invite":
        raise HTTPException(status_code=400, detail="UNSUPPORTED_NOTIFICATION")
    invite_id_raw = (n.payload or {}).get("invite_id")
    if not invite_id_raw:
        raise HTTPException(status_code=400, detail="INVALID_PAYLOAD")
    team = await sub_team_service.accept_sub_team_invite_by_id(
        db, user, UUID(str(invite_id_raw))
    )
    if n.read_at is None:
        await notif_service.mark_read(db, user, notification_id)
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
