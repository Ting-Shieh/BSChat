import asyncio
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="person.enrich", bind=True, max_retries=1)
def process_person_enrich(self, payload: dict) -> None:
    asyncio.run(_process_person_enrich(payload))


async def _process_person_enrich(payload: dict) -> None:
    from app.modules.m3_5_person.service import run_person_enrich_url_auto

    await run_person_enrich_url_auto(payload)


def enqueue_person_enrich_url_auto(contact_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Dispatch a background URL-auto person enrich (Pro + auto_on_url)."""
    from app.core.config import get_settings

    settings = get_settings()
    payload = {"contact_id": str(contact_id), "user_id": str(user_id)}

    if settings.use_celery_workers:
        try:
            celery_app.send_task("person.enrich", args=[payload])
            return
        except Exception:
            logger.exception("Celery person.enrich dispatch failed, falling back to in-process")

    try:
        asyncio.get_running_loop().create_task(_process_person_enrich(payload))
    except RuntimeError:
        asyncio.run(_process_person_enrich(payload))
