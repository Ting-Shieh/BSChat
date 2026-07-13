from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media_urls import public_media_url
from app.models.contact import Contact
from app.models.user import User, UserEntitlement
from app.modules.m3_5_person.section_builder import build_person_enrich_section
from app.modules.m6_enrichment.section_builder import build_enrichment_section
from app.schemas.contact import (
    AiInferredSection,
    CardOriginalSection,
    ContactDetailResponse,
    ContactListItem,
    ContactSections,
    ProvenanceField,
)

DORMANT_THRESHOLD_MONTHS = 6


def _preview(items: list, key: str = "value") -> str | None:
    vals = [i.get(key, "") for i in items if isinstance(i, dict) and i.get(key)]
    return " · ".join(vals[:2]) if vals else None


def _dormant_months(created_at: datetime | None) -> int | None:
    if created_at is None:
        return None
    now = datetime.now(UTC)
    ref = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
    days = (now - ref).days
    if days < 0:
        return None
    return days // 30


def to_list_item(
    contact: Contact,
    *,
    company_products_preview: str | None = None,
    company_enrichment_status: str | None = None,
    captured_by_name: str | None = None,
) -> ContactListItem:
    dormant = _dormant_months(contact.created_at)
    return ContactListItem(
        id=contact.id,
        display_name=contact.display_name,
        company_name=contact.company_name,
        title=contact.title,
        responsibility_scope=contact.responsibility_scope,
        responsibility_confidence=contact.responsibility_confidence,
        source_label=contact.source_label,
        review_status=contact.review_status,
        image_url=public_media_url(contact.image_url),
        phones_preview=_preview(contact.phones or []),
        emails_preview=_preview(contact.emails or []),
        company_products_preview=company_products_preview,
        company_enrichment_status=company_enrichment_status,
        captured_by_name=captured_by_name,
        created_at=contact.created_at,
        dormant_months=dormant,
    )


async def to_detail(
    db: AsyncSession,
    contact: Contact,
    *,
    entitlement: UserEntitlement | None = None,
) -> ContactDetailResponse:
    prov_by_name = {p.field_name: p for p in contact.provenance}
    field_values = {
        "name": contact.display_name,
        "company": contact.company_name,
        "title": contact.title,
        "address": contact.address,
        "website": contact.website,
    }
    original_fields = [
        ProvenanceField(
            name=n,
            value=field_values[n],
            source=prov_by_name[n].source if n in prov_by_name else "ocr",
            confidence=prov_by_name[n].confidence if n in prov_by_name else None,
        )
        for n in field_values
    ]

    ai_section = AiInferredSection()
    if contact.responsibility_scope and (contact.responsibility_confidence or 0) >= 0.6:
        ai_section.responsibility_scope = {
            "value": contact.responsibility_scope,
            "confidence": contact.responsibility_confidence,
            "source": "ai_inferred",
        }
    ai_section.person_enrich = await build_person_enrich_section(
        db, contact=contact, entitlement=entitlement
    )

    enrichment_section = await build_enrichment_section(
        db, user_id=contact.user_id, company_id=contact.company_id
    )

    card_image = public_media_url(contact.image_url)

    capturer = await db.get(User, contact.user_id)
    captured_by_name = capturer.display_name if capturer else None

    return ContactDetailResponse(
        id=contact.id,
        company_id=contact.company_id,
        display_name=contact.display_name,
        company_name=contact.company_name,
        title=contact.title,
        phones=contact.phones or [],
        emails=contact.emails or [],
        address=contact.address,
        website=contact.website,
        linkedin_url=contact.linkedin_url,
        source_type=contact.source_type,
        source_label=contact.source_label,
        review_status=contact.review_status,
        image_url=card_image,
        personal_note=contact.personal_note,
        captured_by_name=captured_by_name,
        version=contact.version,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        sections=ContactSections(
            card_original=CardOriginalSection(fields=original_fields, image_url=card_image),
            ai_inferred=ai_section,
            company_enrichment=enrichment_section,
        ),
    )
