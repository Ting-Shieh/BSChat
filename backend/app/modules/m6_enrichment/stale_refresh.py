"""M6 Layer 2 — stale auto-refresh (Pro only).

Finds companies whose enrichment is older than the user's configured interval and
enqueues a background re-enrich (trigger_type=stale_auto). Gated by M1 entitlement:
only runs when plan allows and auto_refresh_enabled is ON (R-12).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User, UserEntitlement
from app.modules.m6_enrichment.service import enqueue_company_enrich


def auto_refresh_active(ent: UserEntitlement) -> bool:
    return ent.person_enrich_mode == "linkedin_llm" and ent.auto_refresh_enabled


async def find_stale_companies(
    db: AsyncSession, *, user_id: uuid.UUID, interval_days: int
) -> list[Company]:
    cutoff = datetime.now(UTC) - timedelta(days=interval_days)
    result = await db.execute(
        select(Company).where(
            Company.user_id == user_id,
            Company.deleted_at.is_(None),
            Company.enrich_status.in_(("completed", "partial")),
            Company.last_enriched_at.isnot(None),
            Company.last_enriched_at < cutoff,
        )
    )
    return list(result.scalars().all())


async def _first_contact_id(db: AsyncSession, company_id: uuid.UUID) -> uuid.UUID | None:
    result = await db.execute(
        select(Contact.id)
        .where(Contact.company_id == company_id, Contact.deleted_at.is_(None))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def scan_user_stale_refresh(db: AsyncSession, user: User) -> dict:
    """Scan + enqueue stale re-enrich for one user. Returns {scanned, queued}."""
    ent = user.entitlement
    if not auto_refresh_active(ent):
        return {"scanned": 0, "queued": 0, "skipped_reason": "auto_refresh_off"}

    stale = await find_stale_companies(db, user_id=user.id, interval_days=ent.auto_refresh_interval_days)
    queued = 0
    for company in stale:
        if company.enrich_status == "pending":
            continue
        contact_id = await _first_contact_id(db, company.id)
        company.enrich_status = "pending"
        await db.flush()
        enqueue_company_enrich(
            company_id=company.id,
            user_id=user.id,
            workspace_id=user.workspace.id,
            contact_id=contact_id,
            company_name=company.display_name,
            contact_website=company.website_url,
            trigger_type="stale_auto",
        )
        queued += 1

    await db.commit()
    return {"scanned": len(stale), "queued": queued}


async def scan_all_users_stale_refresh() -> dict:
    """Scheduler entry — scan every Pro user with auto-refresh ON."""
    from sqlalchemy.orm import selectinload

    from app.core.db import async_session_factory

    total = {"users": 0, "queued": 0}
    async with async_session_factory() as db:
        result = await db.execute(
            select(User)
            .join(UserEntitlement, UserEntitlement.user_id == User.id)
            .where(
                UserEntitlement.person_enrich_mode == "linkedin_llm",
                UserEntitlement.auto_refresh_enabled.is_(True),
            )
            .options(selectinload(User.entitlement), selectinload(User.workspace))
        )
        users = list(result.scalars().all())
        for user in users:
            outcome = await scan_user_stale_refresh(db, user)
            total["users"] += 1
            total["queued"] += outcome.get("queued", 0)
    return total
