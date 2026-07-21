"""Enterprise tenant user + admin APIs."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.config import get_settings
from app.core.db import get_db
from app.models.organization import OrgMember
from app.modules.enterprise import service as ent
from app.modules.enterprise.email import send_enterprise_invite_email
from app.schemas.enterprise import (
    BatchInviteItemResult,
    CreateEnterpriseInviteBatchRequest,
    CreateEnterpriseInviteBatchResponse,
    CreateEnterpriseInviteRequest,
    CreateEnterpriseInviteResponse,
    EnterpriseApplicationCreate,
    EnterpriseApplicationResponse,
    EnterpriseInviteListItem,
    EnterpriseInvitePreview,
    EnterpriseMemberInfo,
    EnterpriseOrgSummary,
    TransferAdminRequest,
)
from app.schemas.org import MyPublicIdentityResponse, MyPublicIdentityUpdate
from app.schemas.team import TeamResponse
from app.modules.m11_public_directory.service import (
    list_my_public_identities,
    update_my_public_identity,
)

router = APIRouter(tags=["enterprise"])
logger = logging.getLogger(__name__)


def _app_response(app) -> EnterpriseApplicationResponse:
    return EnterpriseApplicationResponse(
        id=app.id,
        company_name=app.company_name,
        slug_requested=app.slug_requested,
        contact_email=app.contact_email,
        estimated_seats=app.estimated_seats,
        note=app.note,
        status=app.status,
        resulting_org_id=app.resulting_org_id,
        created_at=app.created_at,
        reviewed_at=app.reviewed_at,
    )


@router.post("/enterprise/applications", response_model=EnterpriseApplicationResponse)
async def create_application(
    body: EnterpriseApplicationCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EnterpriseApplicationResponse:
    app = await ent.submit_application(
        db,
        user,
        company_name=body.company_name,
        contact_email=str(body.contact_email),
        slug_requested=body.slug_requested,
        estimated_seats=body.estimated_seats,
        note=body.note,
    )
    await db.commit()
    return _app_response(app)


@router.get("/enterprise/applications/mine", response_model=list[EnterpriseApplicationResponse])
async def my_applications(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[EnterpriseApplicationResponse]:
    apps = await ent.list_my_applications(db, user.id)
    return [_app_response(a) for a in apps]


@router.get("/enterprise/orgs/{org_id}", response_model=EnterpriseOrgSummary)
async def get_enterprise_org(
    org_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EnterpriseOrgSummary:
    org = await ent.require_primary_admin(db, user, org_id)
    count = await db.scalar(
        select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org.id)
    )
    return EnterpriseOrgSummary(
        org_id=org.id,
        org_name=org.name,
        slug=org.slug,
        is_enterprise=org.is_enterprise,
        primary_admin_user_id=org.primary_admin_user_id,
        seat_limit=org.seat_limit,
        member_count=int(count or 0),
        approved_at=org.approved_at,
    )


@router.get("/enterprise/orgs/{org_id}/members", response_model=list[EnterpriseMemberInfo])
async def list_members(
    org_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[EnterpriseMemberInfo]:
    org = await ent.require_primary_admin(db, user, org_id)
    rows = await ent.list_org_members(db, org.id)
    return [
        EnterpriseMemberInfo(
            user_id=u.id,
            email=u.email,
            display_name=u.display_name,
            role=m.role,
            is_primary_admin=org.primary_admin_user_id == u.id,
            joined_at=m.created_at,
        )
        for m, u in rows
    ]


@router.delete("/enterprise/orgs/{org_id}/members/{user_id}", status_code=204)
async def delete_member(
    org_id: UUID,
    user_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await ent.remove_member(db, user, org_id=org_id, target_user_id=user_id)
    await db.commit()


@router.post("/enterprise/orgs/{org_id}/transfer-admin", response_model=EnterpriseOrgSummary)
async def transfer_admin(
    org_id: UUID,
    body: TransferAdminRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> EnterpriseOrgSummary:
    org = await ent.transfer_primary_admin(
        db, user, org_id=org_id, new_admin_user_id=body.new_admin_user_id
    )
    await db.commit()
    count = await db.scalar(
        select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org.id)
    )
    return EnterpriseOrgSummary(
        org_id=org.id,
        org_name=org.name,
        slug=org.slug,
        is_enterprise=org.is_enterprise,
        primary_admin_user_id=org.primary_admin_user_id,
        seat_limit=org.seat_limit,
        member_count=int(count or 0),
        approved_at=org.approved_at,
    )


@router.post("/enterprise/orgs/{org_id}/invites", response_model=CreateEnterpriseInviteResponse)
async def create_invite(
    org_id: UUID,
    body: CreateEnterpriseInviteRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CreateEnterpriseInviteResponse:
    from app.models.organization import Organization

    invite, raw = await ent.create_enterprise_invite(
        db,
        user,
        org_id=org_id,
        invited_email=str(body.email),
        expires_days=body.expires_days,
    )
    org = await db.get(Organization, org_id)
    assert org is not None
    await db.commit()
    join_path = f"/join/enterprise/{raw}"
    join_url = f"{get_settings().frontend_base_url.rstrip('/')}{join_path}"
    email_sent = False
    try:
        email_sent = await send_enterprise_invite_email(
            to_email=invite.invited_email or str(body.email),
            org_name=org.name,
            inviter_name=user.display_name or user.email,
            join_url=join_url,
            expires_at=invite.expires_at,
        )
    except HTTPException as exc:
        # The invite remains usable and the response retains its copyable link.
        logger.warning("Enterprise invite email failed: %s", exc.detail)
        email_sent = False
    return CreateEnterpriseInviteResponse(
        invite_id=invite.id,
        token=raw,
        org_id=org.id,
        org_name=org.name,
        invited_email=invite.invited_email or str(body.email),
        expires_at=invite.expires_at,
        join_path=join_path,
        email_sent=email_sent,
    )


@router.post(
    "/enterprise/orgs/{org_id}/invites/batch",
    response_model=CreateEnterpriseInviteBatchResponse,
)
async def create_invite_batch(
    org_id: UUID,
    body: CreateEnterpriseInviteBatchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> CreateEnterpriseInviteBatchResponse:
    from app.models.organization import Organization

    raw_results = await ent.create_enterprise_invite_batch(
        db,
        user,
        org_id=org_id,
        emails=[str(e) for e in body.emails],
        expires_days=body.expires_days,
    )
    org = await db.get(Organization, org_id)
    assert org is not None
    await db.commit()

    settings = get_settings()
    items: list[BatchInviteItemResult] = []
    created = 0
    skipped = 0
    for row in raw_results:
        if row["status"] != "created":
            skipped += 1
            items.append(
                BatchInviteItemResult(
                    email=row["email"],
                    status="skipped",
                    reason=row.get("reason"),
                )
            )
            continue
        created += 1
        join_path = row["join_path"]
        join_url = f"{settings.frontend_base_url.rstrip('/')}{join_path}"
        email_sent = False
        try:
            email_sent = await send_enterprise_invite_email(
                to_email=row["email"],
                org_name=org.name,
                inviter_name=user.display_name or user.email,
                join_url=join_url,
                expires_at=row["expires_at"],
            )
        except HTTPException as exc:
            logger.warning("Enterprise batch invite email failed: %s", exc.detail)
            email_sent = False
        items.append(
            BatchInviteItemResult(
                email=row["email"],
                status="created",
                invite_id=row["invite_id"],
                join_path=join_path,
                email_sent=email_sent,
            )
        )
    return CreateEnterpriseInviteBatchResponse(created=created, skipped=skipped, items=items)


@router.get("/enterprise/me/public-identity", response_model=list[MyPublicIdentityResponse])
async def get_my_public_identity(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[MyPublicIdentityResponse]:
    rows = await list_my_public_identities(db, user)
    return [MyPublicIdentityResponse(**row) for row in rows]


@router.patch(
    "/enterprise/orgs/{org_id}/me/public-identity",
    response_model=MyPublicIdentityResponse,
)
async def patch_my_public_identity(
    org_id: UUID,
    body: MyPublicIdentityUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> MyPublicIdentityResponse:
    from app.models.organization import Organization

    stub = await update_my_public_identity(
        db,
        user,
        org_id,
        external_card_url=body.external_card_url,
        title=body.title,
        display_name=body.display_name,
    )
    org = await db.get(Organization, org_id)
    assert org is not None
    from app.modules.m11_public_directory.service import stub_ai_state

    return MyPublicIdentityResponse(
        org_id=org.id,
        org_name=org.name,
        stub_id=stub.id,
        display_name=stub.display_name,
        title=stub.title,
        external_card_url=stub.external_card_url,
        status=stub.status,
        want_ai_recommend=bool(stub.want_ai_recommend),
        ai_state=stub_ai_state(stub),
    )


@router.get("/enterprise/orgs/{org_id}/invites", response_model=list[EnterpriseInviteListItem])
async def list_invites(
    org_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[EnterpriseInviteListItem]:
    await ent.require_primary_admin(db, user, org_id)
    invites = await ent.list_enterprise_invites(db, org_id)
    return [
        EnterpriseInviteListItem(
            invite_id=i.id,
            invited_email=i.invited_email,
            expires_at=i.expires_at,
            use_count=i.use_count,
            max_uses=i.max_uses,
            revoked_at=i.revoked_at,
            created_at=i.created_at,
        )
        for i in invites
    ]


@router.post("/enterprise/invites/{invite_id}/revoke", status_code=204)
async def revoke_invite(
    invite_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await ent.revoke_enterprise_invite(db, user, invite_id)
    await db.commit()


@router.get("/enterprise/invites/{token}", response_model=EnterpriseInvitePreview)
async def preview_invite(token: str, db: AsyncSession = Depends(get_db)) -> EnterpriseInvitePreview:
    invite, org = await ent.preview_enterprise_invite(db, token)
    return EnterpriseInvitePreview(
        org_id=org.id,
        org_name=org.name,
        slug=org.slug,
        invited_email=invite.invited_email,
        expires_at=invite.expires_at,
        is_enterprise=True,
    )


@router.post("/enterprise/invites/{token}/accept", response_model=TeamResponse)
async def accept_invite(
    token: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TeamResponse:
    org = await ent.accept_enterprise_invite(db, user, token)
    await db.commit()
    return TeamResponse(org_id=org.id, org_name=org.name, slug=org.slug)
