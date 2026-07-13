"""M5 Layer 3 live augment orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import consume_live_augment_quota, live_augment_remaining
from app.core.team import get_team_user_ids
from app.models.company import Company
from app.models.contact import Contact
from app.models.query_augmentation import QueryAugmentation
from app.models.search import SearchQuery, SearchResult
from app.models.user import User
from app.modules.m6_enrichment.query_time import query_time_extract

STALE_DAYS = 90


def _company_is_stale(company: Company | None) -> bool:
    if company is None:
        return True
    if company.enrich_status in ("never", "failed", "partial"):
        return True
    if company.last_enriched_at is None:
        return True
    return (datetime.now(UTC) - company.last_enriched_at) > timedelta(days=STALE_DAYS)


async def should_suggest_live(db: AsyncSession, user: User, contact_ids: list[uuid.UUID]) -> bool:
    if live_augment_remaining(user.entitlement) <= 0:
        return False
    team_ids = set(await get_team_user_ids(db, user.id))
    for cid in contact_ids[:10]:
        contact = await db.get(Contact, cid)
        if not contact or contact.user_id not in team_ids or not contact.company_id:
            continue
        company = await db.get(Company, contact.company_id)
        if _company_is_stale(company):
            return True
    return False


def _append_live_reason(reason: str, products: list[str]) -> str:
    if not products:
        return reason
    snippet = "、".join(products[:3])
    suffix = f"；本次查詢：公司產品包含 {snippet}（即時查詢）"
    if "（即時查詢）" in reason:
        return reason
    return f"{reason}{suffix}"


async def _apply_products_to_rows(
    db: AsyncSession,
    *,
    query_id: uuid.UUID,
    company_id: uuid.UUID,
    products: list[str],
    source_urls: list,
    confidence: float | None,
    user_id: uuid.UUID,
) -> None:
    res = await db.execute(select(SearchResult).where(SearchResult.query_id == query_id))
    for row in res.scalars().all():
        contact = await db.get(Contact, row.contact_id)
        if not contact or contact.company_id != company_id:
            continue
        row.live_products = products
        row.match_reason = _append_live_reason(row.match_reason, products)

    db.add(
        QueryAugmentation(
            user_id=user_id,
            company_id=company_id,
            query_id=query_id,
            live_products=products,
            source_urls=source_urls,
            confidence=confidence,
        )
    )


async def run_live_augment(
    db: AsyncSession,
    user: User,
    query_id: uuid.UUID,
    *,
    contact_ids: list[uuid.UUID] | None = None,
) -> dict:
    """Run query-time live extract for stale result companies; one quota per company."""
    result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_id, SearchQuery.user_id == user.id)
    )
    query_row = result.scalar_one_or_none()
    if not query_row:
        raise HTTPException(status_code=404, detail="Query not found")
    if query_row.status != "COMPLETED":
        raise HTTPException(status_code=409, detail="QUERY_NOT_COMPLETED")

    res = await db.execute(
        select(SearchResult).where(SearchResult.query_id == query_id).order_by(SearchResult.rank)
    )
    rows = list(res.scalars().all())
    if not rows:
        raise HTTPException(status_code=409, detail="NO_RESULTS")

    filter_ids = set(contact_ids) if contact_ids else None
    target_company_ids: list[uuid.UUID] = []
    seen: set[uuid.UUID] = set()
    team_ids = set(await get_team_user_ids(db, user.id))

    for row in rows:
        if filter_ids is not None and row.contact_id not in filter_ids:
            continue
        if row.live_products:
            continue
        contact = await db.get(Contact, row.contact_id)
        if not contact or contact.user_id not in team_ids or not contact.company_id:
            continue
        if contact.company_id in seen:
            continue
        company = await db.get(Company, contact.company_id)
        if not _company_is_stale(company):
            continue
        seen.add(contact.company_id)
        target_company_ids.append(contact.company_id)

    if not target_company_ids:
        raise HTTPException(status_code=409, detail="NOTHING_TO_AUGMENT")

    augmented = 0
    for company_id in target_company_ids:
        if live_augment_remaining(user.entitlement) <= 0:
            break
        extracted = await query_time_extract(db, company_id=company_id, user_id=user.id)
        if not extracted:
            continue
        products = extracted.get("main_products") or []
        if not products:
            continue
        await consume_live_augment_quota(db, user.entitlement)
        await _apply_products_to_rows(
            db,
            query_id=query_id,
            company_id=company_id,
            products=products,
            source_urls=extracted.get("source_urls") or [],
            confidence=extracted.get("confidence"),
            user_id=user.id,
        )
        augmented += 1

    if augmented == 0:
        raise HTTPException(status_code=409, detail="LIVE_AUGMENT_FAILED")

    query_row.live_augmentation_used = True
    query_row.suggest_live = False
    await db.commit()

    return {
        "status": "LIVE_AUGMENTED",
        "augmented_count": augmented,
        "quota_remaining": live_augment_remaining(user.entitlement),
    }
