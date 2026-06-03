"""Apply M3 responsibility inference to contacts."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.responsibility_inference import infer_responsibility, scope_title_similarity
from app.models.company import CompanyEnrichment
from app.models.contact import Contact

CONFIDENCE_GATE = 0.6
PASS2_MIN_ENRICH_CONF = 0.5


async def _latest_products(
    db: AsyncSession, company_id: uuid.UUID | None
) -> tuple[list[str], float | None]:
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


def _adjust_confidence(output, title: str):
    if scope_title_similarity(output.scope, title) > 0.85:
        output.confidence = min(output.confidence, 0.55)
    return output


async def run_inference_for_contact(
    db: AsyncSession,
    contact_id: uuid.UUID,
    *,
    pass_number: int = 1,
) -> bool:
    """Run inference; returns True if responsibility_scope was written."""
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        return False

    title = (contact.title or "").strip()
    if not title:
        return False

    products: list[str] = []
    enrich_conf: float | None = None
    if pass_number >= 2:
        if not contact.company_id:
            return False
        products, enrich_conf = await _latest_products(db, contact.company_id)
        if not products or (enrich_conf or 0) < PASS2_MIN_ENRICH_CONF:
            return False

    output, _model, _pv = await infer_responsibility(
        title=title,
        company_name=contact.company_name,
        company_products=products if pass_number >= 2 else None,
        pass_number=pass_number,
    )
    output = _adjust_confidence(output, title)

    if output.confidence < CONFIDENCE_GATE:
        return False

    if pass_number >= 2:
        old_conf = contact.responsibility_confidence or 0.0
        if output.confidence <= old_conf:
            return False

    contact.responsibility_scope = output.scope
    contact.responsibility_confidence = output.confidence
    await db.commit()

    from app.workers.tasks.contact_index import enqueue_contact_index

    enqueue_contact_index(contact.id)
    return True


async def run_pass2_for_company(db: AsyncSession, company_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Contact.id).where(
            Contact.company_id == company_id,
            Contact.deleted_at.is_(None),
        )
    )
    for (contact_id,) in result.all():
        await run_inference_for_contact(db, contact_id, pass_number=2)
