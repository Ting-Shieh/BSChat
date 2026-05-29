import asyncio
import logging

from app.core.db import async_session_factory
from app.modules.m6_enrichment.enrichment_runner import run_company_enrich, should_skip_dedupe
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="companies.enrich", bind=True, max_retries=1)
def process_company_enrich(self, payload: dict) -> None:
    asyncio.run(_process_company_enrich(payload))


async def _process_company_enrich(payload: dict) -> None:
    import uuid

    from sqlalchemy import select

    from app.models.company import Company

    company_id = uuid.UUID(payload["company_id"])
    user_id = uuid.UUID(payload["user_id"])
    contact_id = uuid.UUID(payload["contact_id"]) if payload.get("contact_id") else None
    trigger_type = payload.get("trigger_type", "ingest")

    async with async_session_factory() as db:
        result = await db.execute(select(Company).where(Company.id == company_id))
        company = result.scalar_one_or_none()
        if company and should_skip_dedupe(company, trigger_type):
            logger.info("Skip enrich dedupe company=%s", company_id)
            return

        await run_company_enrich(
            db,
            company_id=company_id,
            user_id=user_id,
            contact_id=contact_id,
            company_name=payload["company_name"],
            contact_website=payload.get("contact_website"),
            trigger_type=trigger_type,
        )
