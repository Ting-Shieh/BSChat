import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contact import Contact, ContactFieldProvenance
from app.models.contact_search_document import ContactSearchDocument
from app.modules.m6_enrichment.service import dispatch_company_enrich, trigger_enrich_for_contact
from app.schemas.events.contact_upsert import ContactUpsertRequested
from app.workers.tasks.contact_index import enqueue_contact_index

PROVENANCE_FIELDS = ["name", "company", "title", "address", "website"]


def map_review_status(m2_status: str) -> str:
    if m2_status in ("confirmed", "auto_accepted"):
        return "confirmed"
    return "unconfirmed"


def _phones_json(raw: list[str]) -> list[dict]:
    return [{"value": p, "normalized": p, "primary": i == 0} for i, p in enumerate(raw) if p]


def _emails_json(raw: list[str]) -> list[dict]:
    return [{"value": e, "primary": i == 0} for i, e in enumerate(raw) if e]


def _build_search_text(
    display_name: str | None,
    company_name: str | None,
    title: str | None,
    source_label: str | None,
    phones: list[dict],
    emails: list[dict],
) -> str:
    parts = [
        display_name or "",
        company_name or "",
        title or "",
        source_label or "",
        " ".join(p.get("value", "") for p in phones),
        " ".join(e.get("value", "") for e in emails),
    ]
    return " | ".join(p for p in parts if p)


async def upsert_from_payload(db: AsyncSession, payload: dict) -> Contact:
    event = ContactUpsertRequested.model_validate(payload)
    fields = event.parsed_fields()
    raw_card_id = uuid.UUID(event.rawCardId)
    user_id = uuid.UUID(event.userId)
    workspace_id = uuid.UUID(event.workspaceId)
    confidences = event.fieldConfidences or {}

    display_name = fields.name or "未命名"
    phones = _phones_json(fields.phones)
    emails = _emails_json(fields.emails)
    review_status = map_review_status(event.reviewStatus)
    search_text = _build_search_text(
        display_name, fields.company, fields.title, event.sourceLabel, phones, emails
    )

    result = await db.execute(
        select(Contact)
        .where(Contact.raw_card_id == raw_card_id)
        .options(selectinload(Contact.provenance))
    )
    contact = result.scalar_one_or_none()

    if contact is None:
        contact = Contact(
            user_id=user_id,
            workspace_id=workspace_id,
            raw_card_id=raw_card_id,
            version=1,
        )
        db.add(contact)
    else:
        contact.version += 1

    contact.display_name = display_name
    contact.company_name = fields.company
    contact.title = fields.title
    contact.phones = phones
    contact.emails = emails
    contact.address = fields.address
    contact.website = fields.website
    contact.source_type = event.sourceType
    contact.source_label = event.sourceLabel
    contact.capture_method = event.captureMethod
    contact.image_url = event.imageUrl
    contact.review_status = review_status
    contact.search_text = search_text
    contact.search_status = "pending_index"

    await db.flush()
    await _upsert_provenance(db, contact, fields, confidences, raw_card_id)

    should_enqueue = False
    if fields.company:
        should_enqueue = await trigger_enrich_for_contact(db, contact, trigger_type="ingest")

    await db.commit()
    await db.refresh(contact)

    if should_enqueue:
        dispatch_company_enrich(contact, trigger_type="ingest")

    enqueue_contact_index(contact.id)

    return contact


async def _upsert_provenance(
    db: AsyncSession,
    contact: Contact,
    fields,
    confidences: dict[str, float],
    source_ref: uuid.UUID,
) -> None:
    mapping = {
        "name": fields.name,
        "company": fields.company,
        "title": fields.title,
        "address": fields.address,
        "website": fields.website,
    }
    for field_name, value in mapping.items():
        result = await db.execute(
            select(ContactFieldProvenance).where(
                ContactFieldProvenance.contact_id == contact.id,
                ContactFieldProvenance.field_name == field_name,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ContactFieldProvenance(contact_id=contact.id, field_name=field_name)
            db.add(row)
        row.current_value = value
        row.source = "ocr"
        row.source_ref = source_ref
        row.confidence = confidences.get(field_name)


async def list_contacts(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    limit: int = 50,
    review_status: str | None = None,
) -> tuple[list[Contact], int]:
    q = select(Contact).where(Contact.user_id == user_id, Contact.deleted_at.is_(None))
    if review_status:
        q = q.where(Contact.review_status == review_status)
    q = q.order_by(Contact.updated_at.desc())

    result = await db.execute(q)
    all_rows = list(result.scalars().all())
    total = len(all_rows)
    start = (page - 1) * limit
    return all_rows[start : start + limit], total


async def get_contact(db: AsyncSession, contact_id: uuid.UUID, user_id: uuid.UUID) -> Contact | None:
    result = await db.execute(
        select(Contact)
        .where(Contact.id == contact_id, Contact.user_id == user_id, Contact.deleted_at.is_(None))
        .options(selectinload(Contact.provenance))
    )
    return result.scalar_one_or_none()


async def soft_delete_contact(db: AsyncSession, contact: Contact) -> None:
    contact.deleted_at = datetime.now(UTC)
    doc = await db.get(ContactSearchDocument, contact.id)
    if doc:
        await db.delete(doc)
    await db.commit()
