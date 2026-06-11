import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.entitlements import is_person_enrich_allowed
from app.models.contact import Contact, ContactFieldProvenance
from app.models.contact_search_document import ContactSearchDocument
from app.modules.m6_enrichment.service import dispatch_company_enrich, trigger_enrich_for_contact
from app.schemas.events.contact_upsert import ContactUpsertRequested
from app.workers.tasks.contact_index import enqueue_contact_index
from app.workers.tasks.contact_inference import enqueue_contact_inference

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

    if contact.deleted_at is not None:
        contact.deleted_at = None

    contact.display_name = display_name
    contact.company_name = fields.company
    contact.title = fields.title
    contact.phones = phones
    contact.emails = emails
    contact.address = fields.address
    contact.website = fields.website
    if fields.linkedin_url:
        contact.linkedin_url = fields.linkedin_url.strip()
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

    if fields.title and fields.title.strip():
        enqueue_contact_inference(contact.id, pass_number=1)

    if (
        fields.linkedin_url
        and contact.linkedin_url
        and user_id
    ):
        from app.models.user import UserEntitlement

        ent_result = await db.execute(
            select(UserEntitlement).where(UserEntitlement.user_id == user_id)
        )
        ent = ent_result.scalar_one_or_none()
        if (
            ent
            and ent.person_enrich_mode == "linkedin_llm"
            and ent.person_linkedin_auto_on_url
        ):
            from app.workers.tasks.person_enrich import enqueue_person_enrich_url_auto

            enqueue_person_enrich_url_auto(contact.id, user_id)

    return contact


async def get_active_contact_by_raw_card(
    db: AsyncSession,
    raw_card_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Contact | None:
    result = await db.execute(
        select(Contact).where(
            Contact.raw_card_id == raw_card_id,
            Contact.user_id == user_id,
            Contact.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


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


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


async def update_contact_fields(
    db: AsyncSession,
    contact: Contact,
    *,
    fields: dict,
    expected_version: int,
    entitlement=None,
) -> tuple[Contact, bool]:
    """Apply manual edits. Returns (contact, should_dispatch_enrich)."""
    if contact.version != expected_version:
        raise HTTPException(status_code=409, detail="CONTACT_VERSION_CONFLICT")

    old_company = (contact.company_name or "").strip()
    old_title = (contact.title or "").strip()
    old_linkedin = (contact.linkedin_url or "").strip()

    if "display_name" in fields:
        name = _normalize_optional_str(fields["display_name"])
        contact.display_name = name or "未命名"
    if "company_name" in fields:
        contact.company_name = _normalize_optional_str(fields["company_name"])
    if "title" in fields:
        contact.title = _normalize_optional_str(fields["title"])
    if "address" in fields:
        contact.address = _normalize_optional_str(fields["address"])
    if "website" in fields:
        contact.website = _normalize_optional_str(fields["website"])
    if "phone" in fields:
        phone = _normalize_optional_str(fields["phone"])
        contact.phones = _phones_json([phone]) if phone else []
    if "email" in fields:
        email = _normalize_optional_str(fields["email"])
        contact.emails = _emails_json([email]) if email else []
    if "linkedin_url" in fields:
        contact.linkedin_url = _normalize_optional_str(fields["linkedin_url"])
    if "person_scope" in fields:
        if entitlement is None or not is_person_enrich_allowed(entitlement):
            raise HTTPException(status_code=403, detail="PERSON_ENRICH_NOT_ALLOWED")
        from app.modules.m3_5_person.service import clear_person_scope, write_manual_person_scope

        raw_scope = fields["person_scope"]
        if raw_scope is None or not str(raw_scope).strip():
            await clear_person_scope(db, contact)
        else:
            await write_manual_person_scope(db, contact, str(raw_scope).strip())

    linkedin_changed = (
        "linkedin_url" in fields and (contact.linkedin_url or "").strip() != old_linkedin
    )

    company_changed = "company_name" in fields and (contact.company_name or "").strip() != old_company
    title_changed = "title" in fields and (contact.title or "").strip() != old_title

    provenance_map = {
        "name": contact.display_name,
        "company": contact.company_name,
        "title": contact.title,
        "address": contact.address,
        "website": contact.website,
    }
    for field_name, value in provenance_map.items():
        if field_name == "name" and "display_name" not in fields:
            continue
        if field_name == "company" and "company_name" not in fields:
            continue
        if field_name == "title" and "title" not in fields:
            continue
        if field_name == "address" and "address" not in fields:
            continue
        if field_name == "website" and "website" not in fields:
            continue
        await _set_manual_provenance(db, contact, field_name, value)

    contact.search_text = _build_search_text(
        contact.display_name,
        contact.company_name,
        contact.title,
        contact.source_label,
        contact.phones or [],
        contact.emails or [],
    )
    contact.search_status = "pending_index"
    contact.version += 1
    await db.flush()

    should_enqueue = False
    enrich_trigger = "company_name_changed"
    if company_changed:
        if contact.company_name:
            should_enqueue = await trigger_enrich_for_contact(db, contact, trigger_type=enrich_trigger)
        else:
            contact.company_id = None
    elif "website" in fields and contact.company_name and contact.company_id:
        should_enqueue = await trigger_enrich_for_contact(db, contact, trigger_type=enrich_trigger)

    await db.commit()

    if should_enqueue:
        dispatch_company_enrich(contact, trigger_type=enrich_trigger)

    enqueue_contact_index(contact.id)

    if title_changed and contact.title:
        enqueue_contact_inference(contact.id, pass_number=1)

    # M3.5: Pro + auto_on_url → auto person enrich when a LinkedIn URL is added/changed.
    if (
        linkedin_changed
        and contact.linkedin_url
        and entitlement is not None
        and entitlement.person_enrich_mode == "linkedin_llm"
        and entitlement.person_linkedin_auto_on_url
    ):
        from app.workers.tasks.person_enrich import enqueue_person_enrich_url_auto

        enqueue_person_enrich_url_auto(contact.id, contact.user_id)

    return contact, should_enqueue


async def _set_manual_provenance(
    db: AsyncSession,
    contact: Contact,
    field_name: str,
    value: str | None,
) -> None:
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
    row.source = "manual"
    row.source_ref = None
    row.confidence = 1.0


async def soft_delete_contact(db: AsyncSession, contact: Contact) -> None:
    contact.deleted_at = datetime.now(UTC)
    doc = await db.get(ContactSearchDocument, contact.id)
    if doc:
        await db.delete(doc)
    await db.commit()
