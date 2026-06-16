import asyncio
import logging
import uuid

from app.core.config import get_settings
from app.core.db import async_session_factory
from app.modules.m11_public_directory.index_builder import index_stub, unindex_stub
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(name="public_directory.index", bind=True, max_retries=1)
def process_public_directory_index(self, stub_id: str) -> None:
    asyncio.run(_process_index(uuid.UUID(stub_id)))


@celery_app.task(name="public_directory.unindex", bind=True, max_retries=1)
def process_public_directory_unindex(self, stub_id: str) -> None:
    asyncio.run(_process_unindex(uuid.UUID(stub_id)))


async def _process_index(stub_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        await index_stub(db, stub_id)


async def _process_unindex(stub_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        await unindex_stub(db, stub_id)


def enqueue_stub_index(stub_id: uuid.UUID) -> None:
    if settings.use_celery_workers:
        try:
            celery_app.send_task("public_directory.index", args=[str(stub_id)])
            return
        except Exception:
            logger.exception("Celery public_directory.index failed, falling back to in-process")

    try:
        asyncio.get_running_loop().create_task(_process_index(stub_id))
    except RuntimeError:
        asyncio.run(_process_index(stub_id))


def enqueue_stub_unindex(stub_id: uuid.UUID) -> None:
    if settings.use_celery_workers:
        try:
            celery_app.send_task("public_directory.unindex", args=[str(stub_id)])
            return
        except Exception:
            logger.exception("Celery public_directory.unindex failed, falling back to in-process")

    try:
        asyncio.get_running_loop().create_task(_process_unindex(stub_id))
    except RuntimeError:
        asyncio.run(_process_unindex(stub_id))
