import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.models.company import Company, CompanyEnrichment
from app.modules.m3_contacts.detail_builder import to_detail, to_list_item
from app.modules.m3_contacts.upsert import (
    get_contact,
    list_contacts,
    soft_delete_contact,
    update_contact_fields,
)
from app.modules.m6_enrichment.section_builder import products_preview
from app.schemas.contact import (
    ContactDetailResponse,
    ContactListResponse,
    ContactUpdateRequest,
)

router = APIRouter()


@router.get("/contacts", response_model=ContactListResponse)
async def get_contacts(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    review_status: str | None = None,
) -> ContactListResponse:
    items, total = await list_contacts(db, user.id, page=page, limit=limit, review_status=review_status)
    previews = await _batch_list_enrichment(db, items)
    return ContactListResponse(
        items=[
            to_list_item(
                c,
                company_products_preview=previews.get(c.id, {}).get("preview"),
                company_enrichment_status=previews.get(c.id, {}).get("status"),
            )
            for c in items
        ],
        total=total,
    )


@router.get("/contacts/{contact_id}", response_model=ContactDetailResponse)
async def get_contact_detail(
    contact_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactDetailResponse:
    contact = await get_contact(db, contact_id, user.id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return await to_detail(db, contact)


@router.patch("/contacts/{contact_id}", response_model=ContactDetailResponse)
async def patch_contact(
    contact_id: uuid.UUID,
    body: ContactUpdateRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContactDetailResponse:
    contact = await get_contact(db, contact_id, user.id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    payload = body.fields.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="NO_FIELDS_TO_UPDATE")

    field_map = {
        "display_name": "display_name",
        "company_name": "company_name",
        "title": "title",
        "address": "address",
        "website": "website",
        "phone": "phone",
        "email": "email",
    }
    updates = {field_map[k]: v for k, v in payload.items() if k in field_map}

    await update_contact_fields(
        db,
        contact,
        fields=updates,
        expected_version=body.version,
    )
    updated = await get_contact(db, contact_id, user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return await to_detail(db, updated)


@router.delete("/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    contact = await get_contact(db, contact_id, user.id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await soft_delete_contact(db, contact)


async def _batch_list_enrichment(db: AsyncSession, contacts: list) -> dict:
    company_ids = {c.company_id for c in contacts if c.company_id}
    if not company_ids:
        return {}

    company_result = await db.execute(select(Company).where(Company.id.in_(company_ids)))
    companies = {c.id: c for c in company_result.scalars().all()}

    enrich_result = await db.execute(
        select(CompanyEnrichment).where(CompanyEnrichment.company_id.in_(company_ids))
    )
    latest: dict[uuid.UUID, CompanyEnrichment] = {}
    for row in enrich_result.scalars().all():
        prev = latest.get(row.company_id)
        if prev is None or row.enrich_version > prev.enrich_version:
            latest[row.company_id] = row

    out: dict = {}
    for contact in contacts:
        if not contact.company_id:
            continue
        company = companies.get(contact.company_id)
        if not company:
            continue
        if company.enrich_status in ("pending", "never"):
            out[contact.id] = {"status": "pending", "preview": None}
            continue
        if company.enrich_status == "failed":
            out[contact.id] = {"status": None, "preview": None}
            continue
        enrichment = latest.get(contact.company_id)
        out[contact.id] = {
            "status": "ready",
            "preview": products_preview(enrichment),
        }
    return out
