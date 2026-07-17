"""Enterprise tenant B: provision, invites, B1 upgrade/downgrade, admin ops."""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.entitlements import apply_plan_preset
from app.models.enterprise_application import EnterpriseApplication
from app.models.organization import OrgMember, Organization
from app.models.public_business_stub import PublicBusinessStub
from app.models.team_invite import TeamInvite
from app.models.user import User, UserEntitlement
from app.modules.team_invite.service import (
    _invite_usable,
    get_invite_by_raw_token,
    hash_invite_token,
)
from app.workers.tasks.public_directory_index import enqueue_stub_unindex

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,98}[a-z0-9]$|^[a-z0-9]{2,100}$")


def normalize_slug(raw: str) -> str:
    slug = raw.strip().lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def assert_valid_slug(slug: str) -> None:
    if not slug or not _SLUG_RE.match(slug):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_SLUG")


async def require_primary_admin(db: AsyncSession, user: User, org_id: uuid.UUID) -> Organization:
    org = await db.get(Organization, org_id)
    if org is None or not org.is_enterprise:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ENTERPRISE_REQUIRED")
    if org.primary_admin_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NOT_PRIMARY_ADMIN")
    return org


async def _member_count(db: AsyncSession, org_id: uuid.UUID) -> int:
    count = await db.scalar(
        select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org_id)
    )
    return int(count or 0)


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    return result.scalar_one_or_none()


async def _ensure_entitlement(db: AsyncSession, user: User) -> UserEntitlement:
    if user.entitlement is not None:
        return user.entitlement
    result = await db.execute(select(UserEntitlement).where(UserEntitlement.user_id == user.id))
    ent = result.scalar_one_or_none()
    if ent is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="NO_ENTITLEMENT")
    user.entitlement = ent
    return ent


async def upgrade_to_enterprise(db: AsyncSession, user: User, member: OrgMember) -> None:
    ent = await _ensure_entitlement(db, user)
    if member.plan_before_enterprise is None:
        member.plan_before_enterprise = ent.plan_tier
    apply_plan_preset(ent, "enterprise")
    await db.flush()


async def downgrade_from_enterprise(db: AsyncSession, user: User, member: OrgMember | None) -> None:
    ent = await _ensure_entitlement(db, user)
    restore = "free"
    if member and member.plan_before_enterprise in ("free", "pro", "enterprise"):
        restore = member.plan_before_enterprise if member.plan_before_enterprise != "enterprise" else "free"
    apply_plan_preset(ent, restore)
    await db.flush()


async def unpublish_user_stubs_in_org(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> int:
    """Unpublish without committing — caller owns the transaction."""
    result = await db.execute(
        select(PublicBusinessStub).where(
            PublicBusinessStub.org_id == org_id,
            PublicBusinessStub.created_by_user_id == user_id,
            PublicBusinessStub.status == "published",
        )
    )
    stubs = list(result.scalars().all())
    for stub in stubs:
        stub.status = "unpublished"
        stub.unpublished_at = datetime.now(UTC)
        enqueue_stub_unindex(stub.id)
    if stubs:
        await db.flush()
    return len(stubs)


async def provision_enterprise_org(
    db: AsyncSession,
    *,
    company_name: str,
    slug: str,
    admin_user: User,
    seat_limit: int | None = None,
) -> Organization:
    slug_norm = normalize_slug(slug)
    assert_valid_slug(slug_norm)

    existing = await db.execute(select(Organization).where(Organization.slug == slug_norm))
    org = existing.scalar_one_or_none()
    if org is not None:
        if org.is_enterprise and org.primary_admin_user_id not in (None, admin_user.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SLUG_TAKEN")
        org.name = company_name.strip() or org.name
        org.is_enterprise = True
        org.primary_admin_user_id = admin_user.id
        org.seat_limit = seat_limit
        org.approved_at = datetime.now(UTC)
    else:
        org = Organization(
            name=company_name.strip(),
            slug=slug_norm,
            is_enterprise=True,
            primary_admin_user_id=admin_user.id,
            seat_limit=seat_limit,
            approved_at=datetime.now(UTC),
        )
        db.add(org)
        await db.flush()

    member_result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == admin_user.id)
    )
    member = member_result.scalar_one_or_none()
    if member is None:
        member = OrgMember(org_id=org.id, user_id=admin_user.id, role="admin")
        db.add(member)
        await db.flush()
    else:
        member.role = "admin"

    await upgrade_to_enterprise(db, admin_user, member)
    await db.flush()
    return org


async def provision_by_admin_email(
    db: AsyncSession,
    *,
    company_name: str,
    slug: str,
    admin_email: str,
    seat_limit: int | None = None,
) -> Organization:
    admin = await _get_user_by_email(db, admin_email)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ADMIN_USER_NOT_FOUND")
    # Load entitlement relationship
    result = await db.execute(
        select(User).options(selectinload(User.entitlement)).where(User.id == admin.id)
    )
    admin = result.scalar_one()
    return await provision_enterprise_org(
        db,
        company_name=company_name,
        slug=slug,
        admin_user=admin,
        seat_limit=seat_limit,
    )


async def submit_application(
    db: AsyncSession,
    user: User,
    *,
    company_name: str,
    contact_email: str,
    slug_requested: str | None = None,
    estimated_seats: int | None = None,
    note: str | None = None,
) -> EnterpriseApplication:
    slug = normalize_slug(slug_requested) if slug_requested else None
    if slug:
        assert_valid_slug(slug)
    app = EnterpriseApplication(
        applicant_user_id=user.id,
        company_name=company_name.strip(),
        slug_requested=slug,
        contact_email=contact_email.strip().lower(),
        estimated_seats=estimated_seats,
        note=note.strip() if note else None,
        status="pending",
    )
    db.add(app)
    await db.flush()
    return app


async def list_my_applications(db: AsyncSession, user_id: uuid.UUID) -> list[EnterpriseApplication]:
    result = await db.execute(
        select(EnterpriseApplication)
        .where(EnterpriseApplication.applicant_user_id == user_id)
        .order_by(EnterpriseApplication.created_at.desc())
    )
    return list(result.scalars().all())


async def approve_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    *,
    reviewed_by: str,
    slug_override: str | None = None,
    seat_limit: int | None = None,
) -> Organization:
    app = await db.get(EnterpriseApplication, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APPLICATION_NOT_FOUND")
    if app.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="APPLICATION_NOT_PENDING")

    result = await db.execute(
        select(User).options(selectinload(User.entitlement)).where(User.id == app.applicant_user_id)
    )
    applicant = result.scalar_one_or_none()
    if applicant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APPLICANT_NOT_FOUND")

    slug = slug_override or app.slug_requested or normalize_slug(app.company_name)
    slug = normalize_slug(slug)
    assert_valid_slug(slug)

    org = await provision_enterprise_org(
        db,
        company_name=app.company_name,
        slug=slug,
        admin_user=applicant,
        seat_limit=seat_limit if seat_limit is not None else app.estimated_seats,
    )
    app.status = "approved"
    app.reviewed_at = datetime.now(UTC)
    app.reviewed_by = reviewed_by
    app.resulting_org_id = org.id
    await db.flush()
    return org


async def reject_application(
    db: AsyncSession,
    application_id: uuid.UUID,
    *,
    reviewed_by: str,
) -> EnterpriseApplication:
    app = await db.get(EnterpriseApplication, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="APPLICATION_NOT_FOUND")
    if app.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="APPLICATION_NOT_PENDING")
    app.status = "rejected"
    app.reviewed_at = datetime.now(UTC)
    app.reviewed_by = reviewed_by
    await db.flush()
    return app


async def create_enterprise_invite(
    db: AsyncSession,
    admin: User,
    *,
    org_id: uuid.UUID,
    invited_email: str,
    expires_days: int = 14,
) -> tuple[TeamInvite, str]:
    org = await require_primary_admin(db, admin, org_id)
    if expires_days < 1 or expires_days > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_EXPIRES_DAYS")
    email = invited_email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_EMAIL")

    raw = secrets.token_urlsafe(24)
    invite = TeamInvite(
        org_id=org.id,
        token_hash=hash_invite_token(raw),
        created_by_user_id=admin.id,
        expires_at=datetime.now(UTC) + timedelta(days=expires_days),
        max_uses=1,
        use_count=0,
        invite_kind="enterprise_seat",
        invited_email=email,
    )
    db.add(invite)
    await db.flush()
    return invite, raw


async def list_enterprise_invites(db: AsyncSession, org_id: uuid.UUID) -> list[TeamInvite]:
    result = await db.execute(
        select(TeamInvite)
        .where(TeamInvite.org_id == org_id, TeamInvite.invite_kind == "enterprise_seat")
        .order_by(TeamInvite.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_enterprise_invite(db: AsyncSession, admin: User, invite_id: uuid.UUID) -> None:
    invite = await db.get(TeamInvite, invite_id)
    if invite is None or invite.invite_kind != "enterprise_seat":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INVITE_NOT_FOUND")
    await require_primary_admin(db, admin, invite.org_id)
    invite.revoked_at = datetime.now(UTC)
    await db.flush()


async def preview_enterprise_invite(
    db: AsyncSession, raw_token: str
) -> tuple[TeamInvite, Organization]:
    invite = await get_invite_by_raw_token(db, raw_token)
    if invite is None or invite.invite_kind != "enterprise_seat":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INVITE_NOT_FOUND")
    _invite_usable(invite)
    org = await db.get(Organization, invite.org_id)
    if org is None or not org.is_enterprise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ORG_NOT_FOUND")
    return invite, org


async def accept_enterprise_invite(db: AsyncSession, user: User, raw_token: str) -> Organization:
    invite, org = await preview_enterprise_invite(db, raw_token)

    if invite.invited_email and user.email.strip().lower() != invite.invited_email.strip().lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="INVITE_EMAIL_MISMATCH")

    member_result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == user.id)
    )
    member = member_result.scalar_one_or_none()
    if member is not None:
        # Already in org — still ensure enterprise plan
        await upgrade_to_enterprise(db, user, member)
        return org

    if org.seat_limit is not None:
        count = await _member_count(db, org.id)
        if count >= org.seat_limit:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SEAT_LIMIT_REACHED")

    member = OrgMember(org_id=org.id, user_id=user.id, role="member")
    db.add(member)
    await db.flush()
    await upgrade_to_enterprise(db, user, member)
    invite.use_count += 1
    await db.flush()
    return org


async def list_org_members(
    db: AsyncSession, org_id: uuid.UUID
) -> list[tuple[OrgMember, User]]:
    result = await db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(OrgMember.org_id == org_id)
        .order_by(OrgMember.created_at)
    )
    return [(row[0], row[1]) for row in result.all()]


async def remove_member(
    db: AsyncSession,
    admin: User,
    *,
    org_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> None:
    org = await require_primary_admin(db, admin, org_id)
    if target_user_id == org.primary_admin_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="CANNOT_REMOVE_PRIMARY_ADMIN"
        )

    member_result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == target_user_id)
    )
    member = member_result.scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MEMBER_NOT_FOUND")

    target = await db.execute(
        select(User).options(selectinload(User.entitlement)).where(User.id == target_user_id)
    )
    target_user = target.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")

    await unpublish_user_stubs_in_org(db, org.id, target_user_id)
    await downgrade_from_enterprise(db, target_user, member)
    await db.delete(member)
    await db.flush()


async def transfer_primary_admin(
    db: AsyncSession,
    admin: User,
    *,
    org_id: uuid.UUID,
    new_admin_user_id: uuid.UUID,
) -> Organization:
    org = await require_primary_admin(db, admin, org_id)
    if new_admin_user_id == admin.id:
        return org

    new_member_result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == new_admin_user_id)
    )
    new_member = new_member_result.scalar_one_or_none()
    if new_member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MEMBER_NOT_FOUND")

    old_member_result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org.id, OrgMember.user_id == admin.id)
    )
    old_member = old_member_result.scalar_one_or_none()
    if old_member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MEMBER_NOT_FOUND")

    old_member.role = "member"
    new_member.role = "admin"
    org.primary_admin_user_id = new_admin_user_id
    await db.flush()
    return org
