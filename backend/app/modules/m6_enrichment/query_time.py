"""Query-time company extract for M5 Layer 3 live augment (DDR-36: no M6 cache write)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.enrich import extract_company_info
from app.models.company import Company
from app.modules.m6_enrichment.page_fetcher import fetch_pages
from app.modules.m6_enrichment.website_discovery import discover_website


async def query_time_extract(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict | None:
    """Fetch website + LLM extract; returns live snapshot without persisting to company_enrichments."""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
            Company.deleted_at.is_(None),
        )
    )
    company = result.scalar_one_or_none()
    if not company:
        return None

    website = company.website_url
    if not website:
        website = await discover_website(company.display_name, None, None)
    if website and not website.startswith(("http://", "https://")):
        website = f"https://{website}"
    if not website:
        return None

    source_urls, page_text = await fetch_pages(website)
    if not page_text.strip():
        return None

    output, _duration_ms, _model, _prompt_version = await extract_company_info(
        company.display_name, page_text, source_urls or [website]
    )
    if not output.main_products or output.overall_confidence < 0.3:
        return None

    return {
        "main_products": output.main_products,
        "source_urls": source_urls or [website],
        "confidence": output.overall_confidence,
    }
