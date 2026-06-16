from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media_urls import public_media_url
from app.models.contact import Contact
from app.models.user import UserEntitlement
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


def _preview(items: list, key: str = "value") -> str | None:
    vals = [i.get(key, "") for i in items if isinstance(i, dict) and i.get(key)]
    return " · ".join(vals[:2]) if vals else None


def to_list_item(
    contact: Contact,
    *,
    company_products_preview: str | None = None,
    company_enrichment_status: str | None = None,
) -> ContactListItem:
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
        version=contact.version,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        sections=ContactSections(
            card_original=CardOriginalSection(fields=original_fields, image_url=card_image),
            ai_inferred=ai_section,
            company_enrichment=enrichment_section,
        ),
    )
