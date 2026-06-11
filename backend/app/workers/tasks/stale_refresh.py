import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="companies.stale_scan", bind=True)
def process_stale_scan(self) -> dict:
    return asyncio.run(_process_stale_scan())


async def _process_stale_scan() -> dict:
    from app.modules.m6_enrichment.stale_refresh import scan_all_users_stale_refresh

    outcome = await scan_all_users_stale_refresh()
    logger.info("stale_scan outcome=%s", outcome)
    return outcome
