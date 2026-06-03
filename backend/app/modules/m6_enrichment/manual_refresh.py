"""Manual company re-enrich (M6) with entitlement quota."""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import consume_manual_refresh_quota, manual_refresh_remaining
from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User
from app.modules.m6_enrichment.service import enqueue_company_enrich


async def _resolve_contact(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    contact_id: uuid.UUID | None,
) -> Contact | None:
    if contact_id:
        result = await db.execute(
            select(Contact).where(
                Contact.id == contact_id,
                Contact.user_id == user_id,
                Contact.deleted_at.is_(None),
            )
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        if contact.company_id != company_id:
            raise HTTPException(status_code=400, detail="CONTACT_COMPANY_MISMATCH")
        return contact

    result = await db.execute(
        select(Contact)
        .where(
            Contact.user_id == user_id,
            Contact.company_id == company_id,
            Contact.deleted_at.is_(None),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def request_manual_re_enrich(
    db: AsyncSession,
    user: User,
    company_id: uuid.UUID,
    *,
    contact_id: uuid.UUID | None = None,
) -> dict:
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user.id,
            Company.deleted_at.is_(None),
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.enrich_status == "pending":
        raise HTTPException(status_code=409, detail="ENRICH_IN_PROGRESS")

    remaining = await consume_manual_refresh_quota(db, user.entitlement)
    contact = await _resolve_contact(db, user_id=user.id, company_id=company_id, contact_id=contact_id)

    company.enrich_status = "pending"
    await db.commit()

    enqueue_company_enrich(
        company_id=company.id,
        user_id=user.id,
        workspace_id=user.workspace.id,
        contact_id=contact.id if contact else None,
        company_name=company.display_name,
        contact_website=contact.website if contact else company.website_url,
        trigger_type="manual",
    )

    if remaining < 0:
        remaining = manual_refresh_remaining(user.entitlement)

    return {
        "status": "queued",
        "manual_refresh_remaining_month": remaining,
    }
