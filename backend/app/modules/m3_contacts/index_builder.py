"""Build and upsert contact_search_documents."""

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import CompanyEnrichment
from app.models.contact import Contact
from app.models.contact_search_document import ContactSearchDocument, content_hash_for


async def _latest_products(db: AsyncSession, company_id: uuid.UUID | None) -> tuple[list[str], float | None]:
    if not company_id:
        return [], None
    result = await db.execute(
        select(CompanyEnrichment)
        .where(CompanyEnrichment.company_id == company_id)
        .order_by(CompanyEnrichment.enrich_version.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return [], None
    return list(row.main_products or []), row.overall_confidence


def _phones_text(phones: list) -> str:
    return " ".join(p.get("value", "") for p in phones if isinstance(p, dict) and p.get("value"))


def _emails_text(emails: list) -> str:
    return " ".join(e.get("value", "") for e in emails if isinstance(e, dict) and e.get("value"))


async def build_search_text(db: AsyncSession, contact: Contact) -> str:
    products, _ = await _latest_products(db, contact.company_id)
    # M3.5: only index person_scope when it passed the confidence gate (R-35.2/R-35.3).
    person_scope = ""
    if contact.person_scope and (contact.person_scope_confidence or 0) >= 0.75:
        person_scope = contact.person_scope

    parts = [
        contact.display_name or "",
        contact.company_name or "",
        contact.title or "",
        contact.responsibility_scope or "",
        person_scope,
        contact.source_label or "",
        _phones_text(contact.phones or []),
        _emails_text(contact.emails or []),
        " ".join(products),
    ]
    return " | ".join(p for p in parts if p.strip())


async def index_contact(db: AsyncSession, contact_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.deleted_at.is_(None))
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return

    search_text = await build_search_text(db, contact)
    content_hash = content_hash_for(search_text)

    doc_result = await db.execute(
        select(ContactSearchDocument).where(ContactSearchDocument.contact_id == contact_id)
    )
    doc = doc_result.scalar_one_or_none()
    if doc and doc.content_hash == content_hash:
        contact.search_status = "indexed"
        contact.search_text = search_text
        await db.commit()
        return

    if doc is None:
        doc = ContactSearchDocument(
            contact_id=contact.id,
            user_id=contact.user_id,
            workspace_id=contact.workspace_id,
            search_text=search_text,
            content_hash=content_hash,
        )
        db.add(doc)
    else:
        doc.search_text = search_text
        doc.content_hash = content_hash

    await db.flush()
    await db.execute(
        text(
            """
            UPDATE contact_search_documents
            SET search_vector = to_tsvector('simple', search_text),
                indexed_at = NOW()
            WHERE contact_id = :contact_id
            """
        ),
        {"contact_id": contact.id},
    )
    contact.search_text = search_text
    contact.search_status = "indexed"
    await db.commit()
