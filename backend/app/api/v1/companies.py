import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.models.company import Company, CompanyEnrichment
from app.modules.m6_enrichment.manual_refresh import request_manual_re_enrich
from app.modules.m6_enrichment.section_builder import build_enrichment_section
from app.schemas.company import CompanyDetailResponse, ReEnrichResponse

router = APIRouter()


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyDetailResponse:
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == user.id, Company.deleted_at.is_(None))
    )
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    section = await build_enrichment_section(db, user_id=user.id, company_id=company.id)
    enrich_result = await db.execute(
        select(CompanyEnrichment)
        .where(CompanyEnrichment.company_id == company.id)
        .order_by(CompanyEnrichment.enrich_version.desc())
        .limit(1)
    )
    latest = enrich_result.scalar_one_or_none()

    return CompanyDetailResponse(
        id=company.id,
        display_name=company.display_name,
        website_url=company.website_url,
        enrich_status=company.enrich_status,
        last_enriched_at=company.last_enriched_at,
        enrichment=section,
        latest_enrichment_version=latest.enrich_version if latest else 0,
    )


@router.post("/companies/{company_id}/re-enrich", response_model=ReEnrichResponse)
async def re_enrich_company(
    company_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    contact_id: uuid.UUID | None = Query(default=None),
) -> ReEnrichResponse:
    result = await request_manual_re_enrich(
        db, user, company_id, contact_id=contact_id
    )
    return ReEnrichResponse(**result)
