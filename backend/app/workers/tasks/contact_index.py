import asyncio
import logging
import uuid

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.modules.m3_contacts.index_builder import index_contact
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="contacts.index", bind=True, max_retries=1)
def process_contact_index(self, contact_id: str) -> None:
    asyncio.run(_process_contact_index(uuid.UUID(contact_id)))


async def _process_contact_index(contact_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        await index_contact(db, contact_id)


def enqueue_contact_index(contact_id: uuid.UUID) -> None:
    if settings.use_celery_workers:
        try:
            celery_app.send_task("contacts.index", args=[str(contact_id)])
            return
        except Exception:
            logger.exception("Celery index dispatch failed, falling back to in-process")

    try:
        asyncio.get_running_loop().create_task(_process_contact_index(contact_id))
    except RuntimeError:
        asyncio.run(_process_contact_index(contact_id))
