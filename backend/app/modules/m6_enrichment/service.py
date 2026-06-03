"""Company resolve + enrich dispatch."""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.models.company import Company
from app.models.contact import Contact
from app.modules.m6_enrichment.enrichment_runner import run_company_enrich, should_skip_dedupe
from app.modules.m6_enrichment.normalize import normalize_company_name

logger = logging.getLogger(__name__)
settings = get_settings()


async def resolve_company(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    company_name: str,
    contact_website: str | None = None,
) -> Company:
    normalized = normalize_company_name(company_name)
    result = await db.execute(
        select(Company).where(
            Company.user_id == user_id,
            Company.normalized_name == normalized,
            Company.deleted_at.is_(None),
        )
    )
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(
            user_id=user_id,
            workspace_id=workspace_id,
            normalized_name=normalized,
            display_name=company_name.strip(),
            website_url=contact_website,
            enrich_status="never",
        )
        db.add(company)
        await db.flush()
    else:
        company.display_name = company_name.strip()
        if contact_website and not company.website_url:
            company.website_url = contact_website
        if company.website_url and not company.website_url.startswith(("http://", "https://")):
            company.website_url = f"https://{company.website_url.strip()}"
    return company


async def link_contact_company(db: AsyncSession, contact: Contact, company: Company) -> None:
    contact.company_id = company.id
    contact.company_name = contact.company_name or company.display_name


def _schedule_async(coro) -> None:
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


def enqueue_company_enrich(
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    company_name: str,
    contact_website: str | None,
    contact_id: uuid.UUID | None = None,
    trigger_type: str = "ingest",
) -> None:
    payload = {
        "company_id": str(company_id),
        "user_id": str(user_id),
        "workspace_id": str(workspace_id),
        "contact_id": str(contact_id) if contact_id else None,
        "company_name": company_name,
        "contact_website": contact_website,
        "trigger_type": trigger_type,
    }
    if settings.use_celery_workers:
        try:
            from app.workers.celery_app import celery_app

            celery_app.send_task("companies.enrich", args=[payload])
            return
        except Exception:
            logger.exception("Celery enrich dispatch failed, falling back to in-process")

    _schedule_async(_run_enrich_payload(payload))


async def _run_enrich_payload(payload: dict) -> None:
    async with async_session_factory() as db:
        company_id = uuid.UUID(payload["company_id"])
        user_id = uuid.UUID(payload["user_id"])
        contact_id = uuid.UUID(payload["contact_id"]) if payload.get("contact_id") else None

        result = await db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if company and should_skip_dedupe(company, payload.get("trigger_type", "ingest")):
            return

        await run_company_enrich(
            db,
            company_id=company_id,
            user_id=user_id,
            contact_id=contact_id,
            company_name=payload["company_name"],
            contact_website=payload.get("contact_website"),
            trigger_type=payload.get("trigger_type", "ingest"),
        )


async def trigger_enrich_for_contact(
    db: AsyncSession,
    contact: Contact,
    *,
    trigger_type: str = "ingest",
) -> bool:
    """Resolve company + link contact. Returns True if enrich should be enqueued after commit."""
    if not contact.company_name:
        return False

    company = await resolve_company(
        db,
        user_id=contact.user_id,
        workspace_id=contact.workspace_id,
        company_name=contact.company_name,
        contact_website=contact.website,
    )
    await link_contact_company(db, contact, company)

    if should_skip_dedupe(company, trigger_type):
        return False

    company.enrich_status = "pending"
    await db.flush()
    return True


def dispatch_company_enrich(contact: Contact, *, trigger_type: str = "ingest") -> None:
    if not contact.company_name or not contact.company_id:
        return
    enqueue_company_enrich(
        company_id=contact.company_id,
        user_id=contact.user_id,
        workspace_id=contact.workspace_id,
        contact_id=contact.id,
        company_name=contact.company_name,
        contact_website=contact.website,
        trigger_type=trigger_type,
    )
