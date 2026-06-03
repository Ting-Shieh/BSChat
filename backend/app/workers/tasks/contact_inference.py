import asyncio
import logging
import uuid

from app.core.db import async_session_factory
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="contacts.inference", bind=True, max_retries=1)
def process_contact_inference(self, payload: dict) -> None:
    asyncio.run(_process_contact_inference(payload))


async def _process_contact_inference(payload: dict) -> None:
    from app.modules.m3_contacts.inference_service import run_inference_for_contact, run_pass2_for_company

    pass_number = int(payload.get("pass_number", 1))
    async with async_session_factory() as db:
        if payload.get("company_id"):
            await run_pass2_for_company(db, uuid.UUID(payload["company_id"]))
            return
        contact_id = uuid.UUID(payload["contact_id"])
        await run_inference_for_contact(db, contact_id, pass_number=pass_number)


def enqueue_contact_inference(
    contact_id: uuid.UUID,
    *,
    pass_number: int = 1,
) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    payload = {"contact_id": str(contact_id), "pass_number": pass_number}

    if settings.use_celery_workers:
        try:
            celery_app.send_task("contacts.inference", args=[payload])
            return
        except Exception:
            logger.exception("Celery inference dispatch failed, falling back to in-process")

    try:
        asyncio.get_running_loop().create_task(_process_contact_inference(payload))
    except RuntimeError:
        asyncio.run(_process_contact_inference(payload))


def enqueue_company_inference_pass2(company_id: uuid.UUID) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    payload = {"company_id": str(company_id), "pass_number": 2}

    if settings.use_celery_workers:
        try:
            celery_app.send_task("contacts.inference", args=[payload])
            return
        except Exception:
            logger.exception("Celery inference pass2 dispatch failed, falling back to in-process")

    try:
        asyncio.get_running_loop().create_task(_process_contact_inference(payload))
    except RuntimeError:
        asyncio.run(_process_contact_inference(payload))
