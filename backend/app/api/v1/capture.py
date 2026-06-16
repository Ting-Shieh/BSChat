import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.core.media_urls import public_media_url
from app.core.storage import save_image, sha256_bytes
from app.models.capture import OcrResult, RawCard
from app.modules.m2_capture import service
from app.modules.m2_capture.url_resolver import ImportResolveError, download_card_image, resolve_qr_payload, resolve_url_input
from app.schemas.capture import (
    BatchUploadResponse,
    CaptureSessionResponse,
    CardDetailResponse,
    CardListItem,
    CardListResponse,
    CreateSessionRequest,
    DuplicateWarning,
    ImportCardResponse,
    ImportQrRequest,
    ImportUrlRequest,
    OcrResultSummary,
    RawCardUploadResponse,
    ReviewCardRequest,
    UpdateSessionRequest,
)
from app.workers.tasks.ocr import schedule_card_ocr

router = APIRouter()
logger = logging.getLogger(__name__)


def _ocr_summary(ocr: OcrResult | None) -> OcrResultSummary | None:
    if not ocr:
        return None
    return OcrResultSummary(
        extracted_fields=ocr.extracted_fields,
        field_confidences=ocr.field_confidences,
        overall_confidence=ocr.overall_confidence,
        engine=ocr.engine,
        engine_version=ocr.engine_version,
    )


def _card_detail(card: RawCard) -> CardDetailResponse:
    return CardDetailResponse(
        id=card.id,
        capture_session_id=card.capture_session_id,
        status=card.status,
        review_status=card.review_status,
        review_deferred_at=card.review_deferred_at,
        version=card.version,
        image_url=public_media_url(card.image_url),
        capture_method=card.capture_method,
        source_type=card.source_type,
        source_label=card.source_label,
        created_at=card.created_at,
        ocr_result=_ocr_summary(card.ocr_result),
    )


def _card_list_item(card: RawCard) -> CardListItem:
    fields = card.ocr_result.extracted_fields if card.ocr_result else {}
    return CardListItem(
        id=card.id,
        status=card.status,
        review_status=card.review_status,
        review_deferred_at=card.review_deferred_at,
        capture_method=card.capture_method,
        source_label=card.source_label,
        image_url=public_media_url(card.image_url),
        created_at=card.created_at,
        ocr_summary=_ocr_summary(card.ocr_result),
    )


async def _build_upload_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    card: RawCard,
    image_hash: str,
) -> RawCardUploadResponse:
    duplicate_warning = None
    previous = await service.find_duplicate_by_hash(db, user_id, image_hash, exclude_card_id=card.id)
    if previous:
        duplicate_warning = DuplicateWarning(
            previous_card_id=previous.id,
            scanned_at=previous.created_at,
            message=service.duplicate_hash_message(previous.created_at),
        )
    return RawCardUploadResponse(
        raw_card_id=card.id,
        status=card.status,
        capture_session_id=card.capture_session_id,
        duplicate_warning=duplicate_warning,
    )


async def _upload_one(
    db: AsyncSession,
    user: CurrentUser,
    session_id: uuid.UUID,
    file: UploadFile,
    idempotency_key: str | None,
    capture_method: str,
) -> RawCardUploadResponse:
    session = await service.get_session(db, session_id, user.id)
    if not session or session.status != "active":
        raise HTTPException(status_code=404, detail="Session not found or closed")

    if idempotency_key:
        existing = await service.get_card_by_idempotency(db, user.id, idempotency_key)
        if existing:
            return RawCardUploadResponse(
                raw_card_id=existing.id,
                status=existing.status,
                capture_session_id=existing.capture_session_id,
            )

    data = await file.read()
    if len(data) < 100:
        raise HTTPException(status_code=400, detail="Invalid image file")

    image_hash = sha256_bytes(data)
    card_id = uuid.uuid4()
    ext = "jpg"
    if file.content_type and "png" in file.content_type:
        ext = "png"
    image_url = await save_image(user.id, card_id, data, ext)

    card = await service.create_raw_card(
        db,
        user=user,
        session=session,
        capture_method=capture_method,
        image_url=image_url,
        image_hash=image_hash,
        idempotency_key=idempotency_key,
        card_id=card_id,
    )

    schedule_card_ocr(card.id)

    return await _build_upload_response(db, user.id, card, image_hash)


def _import_preview(fields: dict) -> dict:
    return {
        "name": fields.get("name"),
        "company": fields.get("company"),
        "title": fields.get("title"),
    }


async def _complete_import(
    db: AsyncSession,
    user: CurrentUser,
    *,
    capture_method: str,
    resolved: dict,
    idempotency_key: str | None,
    content_for_hash: str,
) -> ImportCardResponse:
    from app.modules.m3_contacts.upsert import get_active_contact_by_raw_card

    if idempotency_key:
        existing = await service.get_card_by_idempotency(db, user.id, idempotency_key)
        if existing and existing.ocr_result:
            contact = await get_active_contact_by_raw_card(db, existing.id, user.id)
            if contact is None:
                try:
                    await service.emit_handoff(db, existing)
                except Exception as exc:
                    raise HTTPException(status_code=500, detail="Handoff failed") from exc
            return ImportCardResponse(
                raw_card_id=existing.id,
                status=existing.status,
                review_status=existing.review_status,
                capture_method=existing.capture_method,
                extracted_preview=_import_preview(existing.ocr_result.extracted_fields),
            )

    content_hash = sha256_bytes(content_for_hash.encode("utf-8"))
    card = await service.create_import_card(
        db,
        user=user,
        capture_method=capture_method,
        content_hash=content_hash,
        idempotency_key=idempotency_key,
    )
    await service.save_import_result(
        db,
        card,
        resolver_type=resolved["resolver_type"],
        extracted_fields=resolved["fields"],
        field_confidences=resolved["field_confidences"],
        raw_text=resolved.get("raw_text", ""),
    )

    remote_image = resolved.get("image_url")
    if remote_image:
        try:
            image_data, ext = await download_card_image(remote_image)
            stored_url = await save_image(user.id, card.id, image_data, ext)
            await service.attach_card_image(
                db,
                card,
                image_url=stored_url,
                image_hash=sha256_bytes(image_data),
            )
        except ImportResolveError as exc:
            logger.warning("Import image skipped for card %s: %s", card.id, exc)
        except Exception:
            logger.exception("Import image failed for card %s", card.id)

    card = await service.get_card(db, card.id, user.id)
    assert card is not None
    try:
        await service.emit_handoff(db, card)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Handoff failed") from exc

    return ImportCardResponse(
        raw_card_id=card.id,
        status=card.status,
        review_status=card.review_status,
        capture_method=card.capture_method,
        extracted_preview=_import_preview(resolved["fields"]),
    )


@router.post("/cards/import-url", response_model=ImportCardResponse, status_code=201)
async def import_url(
    body: ImportUrlRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ImportCardResponse:
    try:
        resolved = await resolve_url_input(body.url)
    except ImportResolveError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)}) from exc

    key = idempotency_key or sha256_bytes(body.url.strip().encode("utf-8"))[:32]
    if body.force:
        key = f"{key}-force-{uuid.uuid4().hex[:8]}"
    return await _complete_import(
        db,
        user,
        capture_method="url",
        resolved=resolved,
        idempotency_key=key,
        content_for_hash=body.url.strip(),
    )


@router.post("/cards/import-qr", response_model=ImportCardResponse, status_code=201)
async def import_qr(
    body: ImportQrRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ImportCardResponse:
    payload = body.payload.strip()
    try:
        if payload.upper().startswith("BEGIN:VCARD"):
            resolved = resolve_qr_payload(payload)
        elif payload.startswith(("http://", "https://")):
            resolved = await resolve_url_input(payload)
        else:
            resolved = resolve_qr_payload(payload)
    except ImportResolveError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)}) from exc

    key = idempotency_key or sha256_bytes(payload.encode("utf-8"))[:32]
    return await _complete_import(
        db,
        user,
        capture_method="qr",
        resolved=resolved,
        idempotency_key=key,
        content_for_hash=payload,
    )


@router.post("/capture-sessions", response_model=CaptureSessionResponse, status_code=201)
async def create_capture_session(
    body: CreateSessionRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaptureSessionResponse:
    session = await service.create_session(db, user, body.source_type, body.source_label)
    return CaptureSessionResponse.model_validate(session)


@router.patch("/capture-sessions/{session_id}", response_model=CaptureSessionResponse)
async def update_capture_session(
    session_id: uuid.UUID,
    body: UpdateSessionRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaptureSessionResponse:
    session = await service.get_session(db, session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.source_label is not None:
        session.source_label = body.source_label
    if body.status == "closed":
        session = await service.close_session(db, session)
    else:
        await db.commit()
        await db.refresh(session)
    return CaptureSessionResponse.model_validate(session)


@router.get("/capture-sessions/{session_id}", response_model=CaptureSessionResponse)
async def get_capture_session(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CaptureSessionResponse:
    session = await service.get_session(db, session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return CaptureSessionResponse.model_validate(session)


@router.post(
    "/capture-sessions/{session_id}/cards",
    response_model=RawCardUploadResponse,
    status_code=202,
)
async def upload_card(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    image: UploadFile = File(...),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    capture_method: str = Query(default="camera_burst"),
) -> RawCardUploadResponse:
    return await _upload_one(db, user, session_id, image, idempotency_key, capture_method)


@router.post(
    "/capture-sessions/{session_id}/cards/batch",
    response_model=BatchUploadResponse,
    status_code=202,
)
async def upload_cards_batch(
    session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    images: list[UploadFile] = File(...),
) -> BatchUploadResponse:
    if len(images) > 20:
        raise HTTPException(status_code=400, detail="Max 20 images per batch")
    cards = []
    for i, img in enumerate(images):
        key = f"batch-{session_id}-{i}-{img.filename}"
        cards.append(await _upload_one(db, user, session_id, img, key, "camera_burst"))
    return BatchUploadResponse(cards=cards)


@router.get("/cards", response_model=CardListResponse)
async def list_cards(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = None,
    review_status: str | None = None,
    session_id: uuid.UUID | None = None,
) -> CardListResponse:
    cards = await service.list_cards(
        db, user.id, status=status, review_status=review_status, session_id=session_id
    )
    return CardListResponse(items=[_card_list_item(c) for c in cards])


@router.get("/cards/pending-count")
async def pending_count(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int]:
    count = await service.count_pending_review(db, user.id)
    return {"count": count}


@router.get("/cards/{card_id}", response_model=CardDetailResponse)
async def get_card(
    card_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CardDetailResponse:
    card = await service.get_card(db, card_id, user.id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card_detail(card)


@router.patch("/cards/{card_id}/review", response_model=CardDetailResponse)
async def review_card(
    card_id: uuid.UUID,
    body: ReviewCardRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CardDetailResponse:
    card = await service.get_card(db, card_id, user.id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    try:
        card = await service.review_card(
            db,
            card,
            name=body.name,
            company=body.company,
            title=body.title,
            version=body.version,
        )
    except ValueError as exc:
        if str(exc) == "version_conflict":
            raise HTTPException(status_code=409, detail="Version conflict") from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.refresh(card, attribute_names=["ocr_result"])
    await service.emit_handoff(db, card)
    return _card_detail(card)


@router.post("/cards/{card_id}/skip", response_model=CardDetailResponse)
async def skip_review(
    card_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CardDetailResponse:
    card = await service.get_card(db, card_id, user.id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    try:
        card = await service.defer_review(db, card)
    except ValueError as exc:
        code = str(exc)
        if code == "not_pending":
            raise HTTPException(status_code=400, detail="Card is not pending review") from exc
        raise HTTPException(status_code=400, detail="Card is not ready for review") from exc
    return _card_detail(card)


@router.post("/cards/{card_id}/reocr", status_code=202)
async def reocr_card(
    card_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    card = await service.get_card(db, card_id, user.id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not card.image_url:
        raise HTTPException(status_code=400, detail="Card has no image")
    await service.reset_card_for_reocr(db, card)
    schedule_card_ocr(card.id)
    return {"raw_card_id": str(card.id), "status": "queued"}


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    card = await service.get_card(db, card_id, user.id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    await service.soft_delete_card(db, card)
