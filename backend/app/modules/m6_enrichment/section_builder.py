from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyEnrichment, CompanyFieldReview
from app.models.user import UserEntitlement
from app.schemas.contact import CompanyEnrichmentSection


async def build_enrichment_section(
    db: AsyncSession,
    *,
    user_id,
    company_id,
) -> CompanyEnrichmentSection:
    if not company_id:
        return CompanyEnrichmentSection(status="hidden", can_refresh=False)

    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == user_id, Company.deleted_at.is_(None))
    )
    company = result.scalar_one_or_none()
    if not company:
        return CompanyEnrichmentSection(status="hidden", can_refresh=False)

    ent = await _get_entitlement(db, user_id)
    manual_remaining = max(0, ent.manual_refresh_quota_monthly - ent.manual_refresh_used_this_month)

    review_result = await db.execute(
        select(CompanyFieldReview).where(
            CompanyFieldReview.company_id == company.id,
            CompanyFieldReview.user_id == user_id,
            CompanyFieldReview.field_name == "main_products",
        )
    )
    review = review_result.scalar_one_or_none()

    if company.enrich_status == "pending" or company.enrich_status == "never":
        return CompanyEnrichmentSection(status="pending", can_refresh=False)

    if review and review.review_status == "rejected":
        return CompanyEnrichmentSection(
            status="rejected",
            can_refresh=True,
            refresh_quota_remaining=manual_remaining,
        )

    enrichment = await _latest_enrichment(db, company.id)
    conf = enrichment.overall_confidence if enrichment else 0.0
    products = enrichment.main_products if enrichment else []

    if review and review.review_status == "user_override" and review.override_value:
        products = review.override_value if isinstance(review.override_value, list) else products

    if company.enrich_status == "failed" or conf < 0.3:
        return CompanyEnrichmentSection(
            status="failed",
            website_url=company.website_url,
            can_refresh=True,
            refresh_quota_remaining=manual_remaining,
        )

    if company.enrich_status == "partial" or conf < 0.5:
        return CompanyEnrichmentSection(
            status="partial",
            main_products=products or None,
            website_url=company.website_url,
            confidence=conf,
            provenance_label=_provenance_label(enrichment),
            updated_at=_iso(company.last_enriched_at),
            can_refresh=True,
            refresh_quota_remaining=manual_remaining,
            review_status=review.review_status if review else "auto",
        )

    return CompanyEnrichmentSection(
        status="completed",
        main_products=products or None,
        website_url=company.website_url,
        confidence=conf,
        provenance_label=_provenance_label(enrichment),
        updated_at=_iso(company.last_enriched_at),
        can_refresh=True,
        refresh_quota_remaining=manual_remaining,
        review_status=review.review_status if review else "auto",
        needs_review=company.needs_review,
    )


async def _latest_enrichment(db: AsyncSession, company_id) -> CompanyEnrichment | None:
    result = await db.execute(
        select(CompanyEnrichment)
        .where(CompanyEnrichment.company_id == company_id)
        .order_by(CompanyEnrichment.enrich_version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_entitlement(db: AsyncSession, user_id) -> UserEntitlement:
    result = await db.execute(select(UserEntitlement).where(UserEntitlement.user_id == user_id))
    ent = result.scalar_one_or_none()
    if ent:
        return ent
    return UserEntitlement(user_id=user_id)


def _provenance_label(enrichment: CompanyEnrichment | None) -> str | None:
    if not enrichment:
        return None
    conf = int(enrichment.overall_confidence * 100)
    urls = enrichment.source_urls or []
    source = urls[0] if urls else "官網"
    return f"✦ AI 補全 · {source} · {conf}%"


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def products_preview(enrichment: CompanyEnrichment | None) -> str | None:
    if not enrichment or enrichment.overall_confidence < 0.5:
        return None
    products = enrichment.main_products or []
    if not products:
        return None
    return " · ".join(products[:3])
