"""Team create + invite link lifecycle (BSChat-owned; not Clerk Organizations)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember, Organization
from app.models.team_invite import TeamInvite
from app.models.user import User
from app.modules.m11_public_directory.service import ensure_org_membership


def hash_invite_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def create_team(
    db: AsyncSession,
    user: User,
    *,
    name: str,
    slug: str,
) -> Organization:
    slug_norm = slug.strip().lower().replace(" ", "-")
    if not slug_norm or len(slug_norm) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_SLUG")
    existing = await db.execute(select(Organization).where(Organization.slug == slug_norm))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SLUG_TAKEN")
    return await ensure_org_membership(db, user, slug_norm, org_name=name.strip() or None)


async def require_org_member(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> Organization:
    result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(Organization.id == org_id, OrgMember.user_id == user_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_ORG_MEMBER")
    return org


async def create_invite(
    db: AsyncSession,
    user: User,
    *,
    org_id: uuid.UUID,
    expires_days: int = 14,
    max_uses: int = 50,
) -> tuple[TeamInvite, str]:
    org = await require_org_member(db, user.id, org_id)
    if org.is_enterprise:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="USE_ENTERPRISE_INVITE",
        )
    if expires_days < 1 or expires_days > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_EXPIRES_DAYS")
    if max_uses < 1 or max_uses > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_MAX_USES")

    raw = secrets.token_urlsafe(24)
    invite = TeamInvite(
        org_id=org_id,
        token_hash=hash_invite_token(raw),
        created_by_user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=expires_days),
        max_uses=max_uses,
        use_count=0,
        invite_kind="team",
    )
    db.add(invite)
    await db.flush()
    return invite, raw


async def get_invite_by_raw_token(db: AsyncSession, raw_token: str) -> TeamInvite | None:
    token_hash = hash_invite_token(raw_token.strip())
    result = await db.execute(select(TeamInvite).where(TeamInvite.token_hash == token_hash))
    return result.scalar_one_or_none()


def _invite_usable(invite: TeamInvite) -> None:
    now = datetime.now(UTC)
    if invite.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="INVITE_REVOKED")
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="INVITE_EXPIRED")
    if invite.use_count >= invite.max_uses:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="INVITE_EXHAUSTED")


async def preview_invite(db: AsyncSession, raw_token: str) -> tuple[TeamInvite, Organization]:
    invite = await get_invite_by_raw_token(db, raw_token)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INVITE_NOT_FOUND")
    _invite_usable(invite)
    org = await db.get(Organization, invite.org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ORG_NOT_FOUND")
    return invite, org


async def accept_invite(db: AsyncSession, user: User, raw_token: str) -> Organization:
    invite, org = await preview_invite(db, raw_token)
    if getattr(invite, "invite_kind", "team") == "enterprise_seat":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="USE_ENTERPRISE_ACCEPT",
        )
    member = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == user.id)
    )
    already = member.scalar_one_or_none() is not None
    if not already:
        db.add(OrgMember(org_id=org.id, user_id=user.id, role="member"))
        invite.use_count += 1
        await db.flush()
    return org


async def revoke_invite(db: AsyncSession, user: User, invite_id: uuid.UUID) -> None:
    invite = await db.get(TeamInvite, invite_id)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INVITE_NOT_FOUND")
    await require_org_member(db, user.id, invite.org_id)
    invite.revoked_at = datetime.now(UTC)
    await db.flush()
