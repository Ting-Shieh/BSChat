"""Run company enrichment pipeline."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.enrich import extract_company_info
from app.models.company import Company, CompanyEnrichment, EnrichJob
from app.models.contact import Contact
from app.modules.m6_enrichment.page_fetcher import fetch_pages
from app.modules.m6_enrichment.website_discovery import discover_website


async def run_company_enrich(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    contact_id: uuid.UUID | None,
    company_name: str,
    contact_website: str | None,
    trigger_type: str,
) -> None:
    result = await db.execute(select(Company).where(Company.id == company_id, Company.user_id == user_id))
    company = result.scalar_one_or_none()
    if not company:
        return

    job = EnrichJob(
        company_id=company.id,
        user_id=user_id,
        contact_id=contact_id,
        trigger_type=trigger_type,
        status="enriching",
        started_at=datetime.now(UTC),
        idempotency_key=f"enrich:{company.id}:{trigger_type}:{uuid.uuid4().hex[:12]}",
    )
    db.add(job)
    company.enrich_status = "pending"
    await db.commit()

    started = datetime.now(UTC)
    contact_email: str | None = None
    if contact_id:
        contact_row = await db.execute(
            select(Contact.emails).where(Contact.id == contact_id, Contact.user_id == user_id)
        )
        emails = contact_row.scalar_one_or_none()
        if emails:
            primary = next((e for e in emails if isinstance(e, dict) and e.get("primary")), None)
            picked = primary or (emails[0] if emails else None)
            if isinstance(picked, dict):
                contact_email = picked.get("value") or picked.get("normalized")

    website = company.website_url or await discover_website(
        company_name, contact_website, contact_email
    )
    if website and not website.startswith(("http://", "https://")):
        website = f"https://{website}"

    if not website:
        await _finish_failed(db, company, job, started, error_code="NO_WEBSITE")
        return

    company.website_url = website
    source_urls, page_text = await fetch_pages(website)

    if not page_text.strip():
        await _finish_failed(db, company, job, started, error_code="FETCH_FAILED", website=website)
        return

    output, _duration_ms, model, prompt_version = await extract_company_info(
        company_name, page_text, source_urls or [website]
    )

    conf = output.overall_confidence
    if conf < 0.3:
        status = "partial"
        enrich_status = "partial"
    elif conf < 0.5:
        status = "partial"
        enrich_status = "partial"
    else:
        status = "completed"
        enrich_status = "completed"

    if not output.main_products:
        await _finish_failed(db, company, job, started, error_code="NO_PRODUCTS", website=website)
        return

    company.enrich_version += 1
    enrichment = CompanyEnrichment(
        company_id=company.id,
        enrich_version=company.enrich_version,
        main_products=output.main_products,
        summary=output.summary,
        industry_tags=output.industry_tags,
        fields_provenance=output.fields_provenance,
        overall_confidence=conf,
        trigger_type=trigger_type,
        source_urls=source_urls or [website],
        model=model,
        prompt_version=prompt_version,
        status=status,
    )
    db.add(enrichment)
    company.enrich_status = enrich_status
    company.last_enriched_at = datetime.now(UTC)
    company.display_name = company_name

    if contact_id:
        await db.execute(
            update(Contact)
            .where(Contact.id == contact_id, Contact.user_id == user_id)
            .values(company_id=company.id)
        )

    job.status = enrich_status
    job.completed_at = datetime.now(UTC)
    job.latency_ms = int((job.completed_at - started).total_seconds() * 1000)
    await db.commit()

    from app.workers.tasks.contact_index import enqueue_contact_index

    if trigger_type == "stale_auto":
        # Products changed for the whole company → re-index every linked contact.
        rows = await db.execute(
            select(Contact.id).where(
                Contact.company_id == company.id,
                Contact.deleted_at.is_(None),
            )
        )
        for (cid,) in rows.all():
            enqueue_contact_index(cid)
    elif contact_id:
        enqueue_contact_index(contact_id)

    if enrich_status in ("completed", "partial") and conf >= 0.5 and output.main_products:
        from app.workers.tasks.contact_inference import enqueue_company_inference_pass2

        enqueue_company_inference_pass2(company.id)


async def _finish_failed(
    db: AsyncSession,
    company: Company,
    job: EnrichJob,
    started: datetime,
    *,
    error_code: str,
    website: str | None = None,
) -> None:
    if website:
        company.website_url = website
    company.enrich_status = "failed"
    company.last_enriched_at = datetime.now(UTC)
    job.status = "failed"
    job.error_code = error_code
    job.completed_at = datetime.now(UTC)
    job.latency_ms = int((job.completed_at - started).total_seconds() * 1000)
    await db.commit()


def should_skip_dedupe(company: Company, trigger_type: str) -> bool:
    if trigger_type in ("manual", "company_name_changed"):
        return False
    if not company.last_enriched_at:
        return False
    return company.last_enriched_at > datetime.now(UTC) - timedelta(hours=24)
