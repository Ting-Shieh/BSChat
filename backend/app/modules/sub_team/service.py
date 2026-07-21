"""Enterprise sub-team lifecycle (create / invite / leave / dissolve)."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember, Organization
from app.models.sub_team import SubTeam, SubTeamMember
from app.models.team_invite import TeamInvite
from app.models.user import User
from app.modules.team_invite.service import (
    _invite_usable,
    get_invite_by_raw_token,
    hash_invite_token,
    require_org_member,
)


async def _enterprise_membership(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[Organization, OrgMember]:
    result = await db.execute(
        select(Organization, OrgMember)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(
            OrgMember.user_id == user_id,
            Organization.is_enterprise.is_(True),
        )
        .order_by(Organization.created_at.asc())
        .limit(1)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_ENTERPRISE_MEMBER")
    return row[0], row[1]


def _is_primary_admin(org: Organization, user_id: uuid.UUID) -> bool:
    return org.primary_admin_user_id == user_id


async def list_my_sub_teams(db: AsyncSession, user: User) -> list[tuple[SubTeam, str, int]]:
    org, _ = await _enterprise_membership(db, user.id)
    rows = (
        await db.execute(
            select(SubTeam, SubTeamMember.role)
            .join(SubTeamMember, SubTeamMember.sub_team_id == SubTeam.id)
            .where(SubTeam.org_id == org.id, SubTeamMember.user_id == user.id)
            .order_by(SubTeam.created_at.asc())
        )
    ).all()
    out: list[tuple[SubTeam, str, int]] = []
    for team, role in rows:
        count = (
            await db.execute(
                select(func.count())
                .select_from(SubTeamMember)
                .where(SubTeamMember.sub_team_id == team.id)
            )
        ).scalar_one()
        out.append((team, role, int(count)))
    return out


async def create_sub_team(
    db: AsyncSession,
    user: User,
    *,
    name: str,
    description: str | None = None,
) -> SubTeam:
    org, _ = await _enterprise_membership(db, user.id)
    cleaned = name.strip()
    if len(cleaned) < 1 or len(cleaned) > 120:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_NAME")
    existing = await db.execute(
        select(SubTeam).where(
            SubTeam.org_id == org.id,
            func.lower(SubTeam.name) == cleaned.lower(),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="NAME_TAKEN")

    team = SubTeam(
        org_id=org.id,
        name=cleaned,
        description=(description or "").strip() or None,
        created_by_user_id=user.id,
    )
    db.add(team)
    await db.flush()
    db.add(SubTeamMember(sub_team_id=team.id, user_id=user.id, role="owner"))
    await db.flush()
    return team


async def get_sub_team(db: AsyncSession, team_id: uuid.UUID) -> SubTeam:
    team = (
        await db.execute(select(SubTeam).where(SubTeam.id == team_id))
    ).scalar_one_or_none()
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SUB_TEAM_NOT_FOUND")
    return team


async def require_sub_team_member(
    db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID
) -> tuple[SubTeam, SubTeamMember]:
    team = await get_sub_team(db, team_id)
    membership = (
        await db.execute(
            select(SubTeamMember).where(
                SubTeamMember.sub_team_id == team_id,
                SubTeamMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_SUB_TEAM_MEMBER")
    return team, membership


async def require_sub_team_access(
    db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID
) -> tuple[SubTeam, Organization, SubTeamMember | None]:
    """Member or primary admin may view / govern."""
    team = await get_sub_team(db, team_id)
    org = await require_org_member(db, user_id, team.org_id)
    membership = (
        await db.execute(
            select(SubTeamMember).where(
                SubTeamMember.sub_team_id == team_id,
                SubTeamMember.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None and not _is_primary_admin(org, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_SUB_TEAM_MEMBER")
    return team, org, membership


async def list_members(
    db: AsyncSession, team_id: uuid.UUID
) -> list[tuple[SubTeamMember, User]]:
    rows = (
        await db.execute(
            select(SubTeamMember, User)
            .join(User, User.id == SubTeamMember.user_id)
            .where(SubTeamMember.sub_team_id == team_id)
            .order_by(SubTeamMember.joined_at.asc())
        )
    ).all()
    return [(m, u) for m, u in rows]


async def _require_sub_team_owner(
    db: AsyncSession, user_id: uuid.UUID, team_id: uuid.UUID
) -> tuple[SubTeam, SubTeamMember]:
    team, membership = await require_sub_team_member(db, user_id, team_id)
    if membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_OWNER")
    return team, membership


def invite_status(invite: TeamInvite) -> str:
    now = datetime.now(UTC)
    if invite.revoked_at is not None:
        return "revoked"
    if invite.expires_at <= now:
        return "expired"
    if invite.use_count >= invite.max_uses:
        return "accepted"
    return "pending"


async def create_sub_team_invite(
    db: AsyncSession,
    user: User,
    *,
    team_id: uuid.UUID,
    invited_email: str,
    expires_days: int = 14,
) -> tuple[TeamInvite, str, SubTeam, Organization, User]:
    """Owner invites one org member by email (A1). Returns invitee User for F1 notification."""
    from app.modules.notifications import service as notif_service

    team, _ = await _require_sub_team_owner(db, user.id, team_id)
    org = await require_org_member(db, user.id, team.org_id)
    if expires_days < 1 or expires_days > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_EXPIRES_DAYS")

    email = invited_email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_EMAIL")

    invitee = (
        await db.execute(select(User).where(func.lower(User.email) == email))
    ).scalar_one_or_none()
    if invitee is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NOT_ORG_MEMBER")

    membership = (
        await db.execute(
            select(OrgMember).where(
                OrgMember.org_id == team.org_id,
                OrgMember.user_id == invitee.id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="NOT_ORG_MEMBER")

    already = (
        await db.execute(
            select(SubTeamMember).where(
                SubTeamMember.sub_team_id == team.id,
                SubTeamMember.user_id == invitee.id,
            )
        )
    ).scalar_one_or_none()
    if already is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ALREADY_MEMBER")

    pending = (
        await db.execute(
            select(TeamInvite).where(
                TeamInvite.sub_team_id == team.id,
                TeamInvite.invite_kind == "sub_team",
                func.lower(TeamInvite.invited_email) == email,
                TeamInvite.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    for inv in pending:
        if invite_status(inv) == "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PENDING_EXISTS")

    raw = secrets.token_urlsafe(24)
    invite = TeamInvite(
        org_id=team.org_id,
        sub_team_id=team.id,
        token_hash=hash_invite_token(raw),
        created_by_user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=expires_days),
        max_uses=1,
        use_count=0,
        invite_kind="sub_team",
        invited_email=email,
    )
    db.add(invite)
    await db.flush()

    await notif_service.create_notification(
        db,
        user_id=invitee.id,
        kind="sub_team_invite",
        title=f"邀請加入「{team.name}」",
        body=f"{user.display_name or user.email} 邀請你加入子團隊",
        payload={
            "invite_id": str(invite.id),
            "sub_team_id": str(team.id),
            "sub_team_name": team.name,
            "org_name": org.name,
            "inviter_name": user.display_name or user.email,
        },
    )
    return invite, raw, team, org, invitee


async def list_sub_team_invites(
    db: AsyncSession, user: User, team_id: uuid.UUID
) -> list[TeamInvite]:
    """Owner view: only open (pending) invites — revoked/expired/accepted are not listed."""
    await _require_sub_team_owner(db, user.id, team_id)
    rows = (
        await db.execute(
            select(TeamInvite)
            .where(
                TeamInvite.sub_team_id == team_id,
                TeamInvite.invite_kind == "sub_team",
                TeamInvite.revoked_at.is_(None),
                TeamInvite.invited_email.is_not(None),
            )
            .order_by(TeamInvite.created_at.desc())
        )
    ).scalars().all()
    return [i for i in rows if invite_status(i) == "pending"]


async def revoke_sub_team_invite(
    db: AsyncSession, user: User, invite_id: uuid.UUID
) -> None:
    """Hard-delete invite so it disappears from the owner list; dismiss related F1 notifs."""
    from app.models.notification import UserNotification

    invite = (
        await db.execute(select(TeamInvite).where(TeamInvite.id == invite_id))
    ).scalar_one_or_none()
    if invite is None or invite.invite_kind != "sub_team" or invite.sub_team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INVITE_NOT_FOUND")
    await _require_sub_team_owner(db, user.id, invite.sub_team_id)

    invite_id_str = str(invite.id)
    notifs = (
        await db.execute(
            select(UserNotification).where(
                UserNotification.kind == "sub_team_invite",
                UserNotification.payload["invite_id"].as_string() == invite_id_str,
            )
        )
    ).scalars().all()
    for n in notifs:
        await db.delete(n)

    await db.delete(invite)
    await db.flush()


async def accept_sub_team_invite_by_id(
    db: AsyncSession, user: User, invite_id: uuid.UUID
) -> SubTeam:
    invite = (
        await db.execute(select(TeamInvite).where(TeamInvite.id == invite_id))
    ).scalar_one_or_none()
    if invite is None or invite.invite_kind != "sub_team" or invite.sub_team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INVITE_NOT_FOUND")
    if invite_status(invite) != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVITE_NOT_USABLE")
    if invite.invited_email and user.email.strip().lower() != invite.invited_email.strip().lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="EMAIL_MISMATCH")
    return await _accept_invite_row(db, user, invite)


async def _accept_invite_row(db: AsyncSession, user: User, invite: TeamInvite) -> SubTeam:
    assert invite.sub_team_id is not None
    team = await get_sub_team(db, invite.sub_team_id)
    org = (
        await db.execute(select(Organization).where(Organization.id == team.org_id))
    ).scalar_one()
    await require_org_member(db, user.id, org.id)
    if not org.is_enterprise:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_ENTERPRISE")
    if invite.invited_email and user.email.strip().lower() != invite.invited_email.strip().lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="EMAIL_MISMATCH")
    existing = (
        await db.execute(
            select(SubTeamMember).where(
                SubTeamMember.sub_team_id == team.id,
                SubTeamMember.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(SubTeamMember(sub_team_id=team.id, user_id=user.id, role="member"))
        invite.use_count += 1
        await db.flush()
    return team


async def preview_sub_team_invite(
    db: AsyncSession, token: str
) -> tuple[TeamInvite, SubTeam, Organization]:
    invite = await get_invite_by_raw_token(db, token)
    if invite is None or invite.invite_kind != "sub_team" or invite.sub_team_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INVITE_NOT_FOUND")
    _invite_usable(invite)
    team = await get_sub_team(db, invite.sub_team_id)
    org = (
        await db.execute(select(Organization).where(Organization.id == team.org_id))
    ).scalar_one()
    return invite, team, org


async def accept_sub_team_invite(db: AsyncSession, user: User, token: str) -> SubTeam:
    invite, _team, _org = await preview_sub_team_invite(db, token)
    return await _accept_invite_row(db, user, invite)


async def remove_member(
    db: AsyncSession,
    actor: User,
    *,
    team_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> None:
    team, org, membership = await require_sub_team_access(db, actor.id, team_id)
    is_owner = membership is not None and membership.role == "owner"
    is_admin = _is_primary_admin(org, actor.id)
    if not is_owner and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_ALLOWED")
    target = (
        await db.execute(
            select(SubTeamMember).where(
                SubTeamMember.sub_team_id == team_id,
                SubTeamMember.user_id == target_user_id,
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MEMBER_NOT_FOUND")
    if target.role == "owner":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CANNOT_REMOVE_OWNER")
    await db.delete(target)
    await db.flush()


async def leave_sub_team(db: AsyncSession, user: User, team_id: uuid.UUID) -> None:
    team, membership = await require_sub_team_member(db, user.id, team_id)
    if membership.role == "owner":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OWNER_MUST_DISSOLVE")
    await db.delete(membership)
    await db.flush()


async def dissolve_sub_team(db: AsyncSession, user: User, team_id: uuid.UUID) -> None:
    team, org, membership = await require_sub_team_access(db, user.id, team_id)
    is_owner = membership is not None and membership.role == "owner"
    is_admin = _is_primary_admin(org, user.id)
    if not is_owner and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_ALLOWED")
    await db.delete(team)
    await db.flush()


async def list_org_sub_teams(
    db: AsyncSession, user: User, org_id: uuid.UUID
) -> list[tuple[SubTeam, int, str | None]]:
    org = await require_org_member(db, user.id, org_id)
    if not org.is_enterprise or not _is_primary_admin(org, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_PRIMARY_ADMIN")
    teams = (
        await db.execute(
            select(SubTeam).where(SubTeam.org_id == org_id).order_by(SubTeam.created_at.asc())
        )
    ).scalars().all()
    out: list[tuple[SubTeam, int, str | None]] = []
    for team in teams:
        count = (
            await db.execute(
                select(func.count())
                .select_from(SubTeamMember)
                .where(SubTeamMember.sub_team_id == team.id)
            )
        ).scalar_one()
        owner = (
            await db.execute(
                select(User.display_name, User.email)
                .join(SubTeamMember, SubTeamMember.user_id == User.id)
                .where(
                    SubTeamMember.sub_team_id == team.id,
                    SubTeamMember.role == "owner",
                )
                .limit(1)
            )
        ).first()
        owner_label = None
        if owner:
            owner_label = owner[0] or owner[1]
        out.append((team, int(count), owner_label))
    return out
