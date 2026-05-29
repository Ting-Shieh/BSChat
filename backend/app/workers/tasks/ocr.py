import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.pipelines.ocr import extract_from_image_url
from app.core.db import async_session_factory
from app.models.capture import RawCard
from app.modules.m2_capture import service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ocr.process_card", bind=True, max_retries=2)
def process_card_ocr(self, raw_card_id: str) -> None:
    asyncio.run(_process_card_ocr_safe(uuid.UUID(raw_card_id)))


def schedule_card_ocr(card_id: uuid.UUID) -> None:
    """Dispatch OCR without blocking the upload response."""
    try:
        asyncio.get_running_loop().create_task(_process_card_ocr_safe(card_id))
    except RuntimeError:
        asyncio.run(_process_card_ocr_safe(card_id))


async def _process_card_ocr_safe(card_id: uuid.UUID) -> None:
    try:
        await _process_card_ocr(card_id)
    except Exception:
        logger.exception("OCR pipeline failed for card %s", card_id)


async def _process_card_ocr(card_id: uuid.UUID) -> None:
    async with async_session_factory() as db:
        result = await db.execute(
            select(RawCard)
            .where(RawCard.id == card_id)
            .options(selectinload(RawCard.ocr_result))
        )
        card = result.scalar_one_or_none()
        if not card or card.status in ("ocr_done", "ocr_failed"):
            return

        card.status = "ocr_processing"
        await db.commit()

        try:
            if not card.image_url:
                raise ValueError("missing image_url")
            output, duration_ms, engine, engine_version = await extract_from_image_url(card.image_url)
            await service.save_ocr_result(
                db,
                card,
                engine=engine,
                engine_version=engine_version,
                extracted_fields=output.to_extracted_fields(),
                field_confidences=output.field_confidences,
                raw_text=output.raw_text,
                overall_confidence=output.overall_confidence(),
                duration_ms=duration_ms,
            )
            result = await db.execute(
                select(RawCard)
                .where(RawCard.id == card_id)
                .options(selectinload(RawCard.ocr_result))
            )
            card = result.scalar_one()
            try:
                await service.emit_handoff(db, card)
            except Exception:
                logger.exception("M3 handoff failed for card %s (OCR saved)", card_id)
        except Exception as exc:
            await service.mark_ocr_failed(db, card, str(exc))
            logger.exception("OCR failed for card %s: %s", card_id, exc)
