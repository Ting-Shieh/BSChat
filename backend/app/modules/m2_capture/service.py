import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.capture import CaptureSession, HandoffEvent, OcrResult, RawCard
from app.models.contact import Contact
from app.models.contact_search_document import ContactSearchDocument
from app.models.user import User


def review_status_from_confidences(confidences: dict) -> str:
    review_fields = ["name", "company", "title"]
    auto = all(confidences.get(f, 0) >= 0.8 for f in review_fields)
    return "auto_accepted" if auto else "pending_review"


async def create_session(
    db: AsyncSession,
    user: User,
    source_type: str | None,
    source_label: str | None,
) -> CaptureSession:
    session = CaptureSession(
        user_id=user.id,
        workspace_id=user.workspace.id,
        source_type=source_type,
        source_label=source_label,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> CaptureSession | None:
    result = await db.execute(
        select(CaptureSession).where(
            CaptureSession.id == session_id,
            CaptureSession.user_id == user_id,
            CaptureSession.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def close_session(db: AsyncSession, session: CaptureSession) -> CaptureSession:
    session.status = "closed"
    session.closed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(session)
    return session


async def increment_session_counts(db: AsyncSession, session_id: uuid.UUID) -> None:
    await db.execute(
        update(CaptureSession)
        .where(CaptureSession.id == session_id)
        .values(card_count=CaptureSession.card_count + 1)
    )


async def get_card_by_idempotency(
    db: AsyncSession, user_id: uuid.UUID, idempotency_key: str
) -> RawCard | None:
    result = await db.execute(
        select(RawCard)
        .where(
            RawCard.user_id == user_id,
            RawCard.idempotency_key == idempotency_key,
            RawCard.deleted_at.is_(None),
        )
        .options(selectinload(RawCard.ocr_result))
    )
    return result.scalar_one_or_none()


def duplicate_hash_message(scanned_at: datetime) -> str:
    now = datetime.now(UTC)
    scanned = scanned_at.astimezone(UTC) if scanned_at.tzinfo else scanned_at.replace(tzinfo=UTC)
    days = max(0, (now.date() - scanned.date()).days)
    if days == 0:
        return "今天可能掃過相同名片"
    if days == 1:
        return "1 天前可能掃過相同名片"
    return f"{days} 天前可能掃過相同名片"


async def find_duplicate_by_hash(
    db: AsyncSession,
    user_id: uuid.UUID,
    image_hash: str,
    *,
    exclude_card_id: uuid.UUID | None = None,
    within_days: int = 30,
) -> RawCard | None:
    cutoff = datetime.now(UTC) - timedelta(days=within_days)
    q = (
        select(RawCard)
        .where(
            RawCard.user_id == user_id,
            RawCard.image_hash == image_hash,
            RawCard.deleted_at.is_(None),
            RawCard.created_at >= cutoff,
        )
        .order_by(RawCard.created_at.desc())
        .limit(1)
    )
    if exclude_card_id is not None:
        q = q.where(RawCard.id != exclude_card_id)
    result = await db.execute(q)
    return result.scalar_one_or_none()


async def create_raw_card(
    db: AsyncSession,
    *,
    user: User,
    session: CaptureSession | None,
    capture_method: str,
    image_url: str,
    image_hash: str,
    idempotency_key: str | None,
    card_id: uuid.UUID | None = None,
) -> RawCard:
    card = RawCard(
        id=card_id or uuid.uuid4(),
        capture_session_id=session.id if session else None,
        user_id=user.id,
        workspace_id=user.workspace.id,
        capture_method=capture_method,
        image_url=image_url,
        image_hash=image_hash,
        source_type=session.source_type if session else None,
        source_label=session.source_label if session else None,
        status="queued",
        idempotency_key=idempotency_key,
    )
    db.add(card)
    if session:
        session.card_count += 1
    await db.commit()
    await db.refresh(card)
    return card


async def list_cards(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    review_status: str | None = None,
    session_id: uuid.UUID | None = None,
) -> list[RawCard]:
    q = (
        select(RawCard)
        .where(RawCard.user_id == user_id, RawCard.deleted_at.is_(None))
        .options(selectinload(RawCard.ocr_result))
        .order_by(RawCard.created_at.desc())
    )
    if status:
        q = q.where(RawCard.status == status)
    if review_status:
        q = q.where(RawCard.review_status == review_status)
    if session_id:
        q = q.where(RawCard.capture_session_id == session_id)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_card(db: AsyncSession, card_id: uuid.UUID, user_id: uuid.UUID) -> RawCard | None:
    result = await db.execute(
        select(RawCard)
        .where(RawCard.id == card_id, RawCard.user_id == user_id, RawCard.deleted_at.is_(None))
        .options(selectinload(RawCard.ocr_result))
    )
    return result.scalar_one_or_none()


async def soft_delete_card(db: AsyncSession, card: RawCard) -> None:
    if card.capture_session_id:
        session = await db.get(CaptureSession, card.capture_session_id)
        if session:
            if card.review_status == "pending_review" and card.review_deferred_at is None:
                session.pending_count = max(0, session.pending_count - 1)
            elif card.review_status in ("auto_accepted", "confirmed"):
                session.confirmed_count = max(0, session.confirmed_count - 1)

    result = await db.execute(
        select(Contact).where(
            Contact.raw_card_id == card.id,
            Contact.user_id == card.user_id,
            Contact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    if contact:
        contact.deleted_at = datetime.now(UTC)
        doc = await db.get(ContactSearchDocument, contact.id)
        if doc:
            await db.delete(doc)

    card.deleted_at = datetime.now(UTC)
    card.idempotency_key = None
    await db.commit()


async def defer_review(db: AsyncSession, card: RawCard) -> RawCard:
    if card.review_status != "pending_review":
        raise ValueError("not_pending")
    if card.status != "ocr_done":
        raise ValueError("not_ready")
    card.review_deferred_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(card)
    return card


async def count_pending_review(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(RawCard)
        .where(
            RawCard.user_id == user_id,
            RawCard.deleted_at.is_(None),
            RawCard.review_status == "pending_review",
            RawCard.review_deferred_at.is_(None),
            RawCard.status == "ocr_done",
        )
    )
    return result.scalar_one()


async def save_ocr_result(
    db: AsyncSession,
    card: RawCard,
    *,
    engine: str,
    engine_version: str,
    extracted_fields: dict,
    field_confidences: dict,
    raw_text: str,
    overall_confidence: float | None,
    duration_ms: int,
) -> OcrResult:
    review_status = review_status_from_confidences(field_confidences)
    card.status = "ocr_done"
    card.review_status = review_status

    ocr = OcrResult(
        raw_card_id=card.id,
        engine=engine,
        engine_version=engine_version,
        raw_text=raw_text,
        extracted_fields=extracted_fields,
        field_confidences=field_confidences,
        overall_confidence=overall_confidence,
        processed_at=datetime.now(UTC),
        duration_ms=duration_ms,
    )
    db.add(ocr)

    if card.capture_session_id:
        session = await db.get(CaptureSession, card.capture_session_id)
        if session:
            if review_status == "pending_review":
                session.pending_count += 1
            else:
                session.confirmed_count += 1

    await db.commit()
    await db.refresh(card)
    await db.refresh(ocr)
    return ocr


async def mark_ocr_failed(db: AsyncSession, card: RawCard, error: str) -> None:
    card.status = "ocr_failed"
    await db.commit()


async def reset_card_for_reocr(db: AsyncSession, card: RawCard) -> None:
    if card.ocr_result and card.capture_session_id:
        session = await db.get(CaptureSession, card.capture_session_id)
        if session:
            if card.review_status == "pending_review":
                session.pending_count = max(0, session.pending_count - 1)
            elif card.review_status in ("auto_accepted", "confirmed"):
                session.confirmed_count = max(0, session.confirmed_count - 1)

    if card.ocr_result:
        await db.delete(card.ocr_result)
        await db.flush()

    card.status = "queued"
    card.review_status = "pending_review"
    card.review_deferred_at = None
    await db.commit()
    await db.refresh(card)


async def review_card(
    db: AsyncSession,
    card: RawCard,
    *,
    name: str | None,
    company: str | None,
    title: str | None,
    version: int,
) -> RawCard:
    if card.version != version:
        raise ValueError("version_conflict")

    if not card.ocr_result:
        raise ValueError("no_ocr")

    fields = dict(card.ocr_result.extracted_fields)
    if name is not None:
        fields["name"] = name
    if company is not None:
        fields["company"] = company
    if title is not None:
        fields["title"] = title
    card.ocr_result.extracted_fields = fields

    was_pending = card.review_status == "pending_review"
    card.review_status = "confirmed"
    card.review_deferred_at = None
    card.version += 1

    if was_pending and card.capture_session_id:
        session = await db.get(CaptureSession, card.capture_session_id)
        if session and session.pending_count > 0:
            session.pending_count -= 1
        if session:
            session.confirmed_count += 1

    await db.commit()
    await db.refresh(card)
    return card


async def save_import_result(
    db: AsyncSession,
    card: RawCard,
    *,
    resolver_type: str,
    extracted_fields: dict,
    field_confidences: dict,
    raw_text: str,
) -> OcrResult:
    """Persist parsed digital card fields (skips OCR worker)."""
    review_status = review_status_from_confidences(field_confidences)
    card.status = "ocr_done"
    card.review_status = review_status

    ocr = OcrResult(
        raw_card_id=card.id,
        engine="import",
        engine_version=resolver_type,
        raw_text=raw_text,
        extracted_fields=extracted_fields,
        field_confidences=field_confidences,
        overall_confidence=sum(field_confidences.values()) / len(field_confidences)
        if field_confidences
        else None,
        processed_at=datetime.now(UTC),
        duration_ms=0,
    )
    db.add(ocr)
    await db.commit()
    await db.refresh(card)
    await db.refresh(ocr)
    return ocr


async def create_import_card(
    db: AsyncSession,
    *,
    user: User,
    capture_method: str,
    content_hash: str,
    idempotency_key: str | None,
) -> RawCard:
    card = RawCard(
        user_id=user.id,
        workspace_id=user.workspace.id,
        capture_method=capture_method,
        image_url=None,
        image_hash=content_hash,
        status="queued",
        idempotency_key=idempotency_key,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


async def attach_card_image(
    db: AsyncSession,
    card: RawCard,
    *,
    image_url: str,
    image_hash: str,
) -> RawCard:
    card.image_url = image_url
    card.image_hash = image_hash
    await db.commit()
    await db.refresh(card)
    return card


async def emit_handoff(db: AsyncSession, card: RawCard) -> HandoffEvent:
    ocr = card.ocr_result
    fields = ocr.extracted_fields if ocr else {}
    confidences = ocr.field_confidences if ocr else {}
    provenance_source = "import" if card.capture_method in ("url", "qr") else "ocr"
    payload = {
        "eventId": str(uuid.uuid4()),
        "userId": str(card.user_id),
        "workspaceId": str(card.workspace_id),
        "rawCardId": str(card.id),
        "fields": fields,
        "fieldConfidences": confidences,
        "provenance": {"source": provenance_source, "sourceRef": str(card.id)},
        "sourceType": card.source_type,
        "sourceLabel": card.source_label,
        "captureMethod": card.capture_method,
        "imageUrl": card.image_url,
        "reviewStatus": card.review_status,
        "occurredAt": datetime.now(UTC).isoformat(),
    }
    event = HandoffEvent(raw_card_id=card.id, payload=payload)
    db.add(event)
    await db.commit()

    from app.modules.m3_contacts.upsert import upsert_from_payload

    await upsert_from_payload(db, payload)

    return event
