"""Ops endpoints for enterprise provision / approve (dogfood + internal)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.modules.enterprise import service as ent
from app.schemas.enterprise import (
    ApproveApplicationRequest,
    ProvisionEnterpriseRequest,
    ProvisionEnterpriseResponse,
    RejectApplicationRequest,
)

router = APIRouter(prefix="/ops/enterprise", tags=["ops-enterprise"])


def require_ops(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")) -> str:
    settings = get_settings()
    configured = (settings.enterprise_ops_token or "").strip()
    if configured:
        if not x_ops_token or x_ops_token != configured:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OPS_UNAUTHORIZED")
        return "ops"
    if settings.allow_dev_login:
        return "dev"
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OPS_UNAUTHORIZED")


@router.post("/provision", response_model=ProvisionEnterpriseResponse)
async def provision(
    body: ProvisionEnterpriseRequest,
    db: AsyncSession = Depends(get_db),
    _ops: str = Depends(require_ops),
) -> ProvisionEnterpriseResponse:
    org = await ent.provision_by_admin_email(
        db,
        company_name=body.company_name,
        slug=body.slug,
        admin_email=str(body.admin_email),
        seat_limit=body.seat_limit,
    )
    await db.commit()
    assert org.primary_admin_user_id is not None
    return ProvisionEnterpriseResponse(
        org_id=org.id,
        org_name=org.name,
        slug=org.slug,
        primary_admin_user_id=org.primary_admin_user_id,
        is_enterprise=True,
    )


@router.post("/applications/{application_id}/approve", response_model=ProvisionEnterpriseResponse)
async def approve(
    application_id: UUID,
    body: ApproveApplicationRequest,
    db: AsyncSession = Depends(get_db),
    ops: str = Depends(require_ops),
) -> ProvisionEnterpriseResponse:
    org = await ent.approve_application(
        db,
        application_id,
        reviewed_by=body.reviewed_by or ops,
        slug_override=body.slug_override,
        seat_limit=body.seat_limit,
    )
    await db.commit()
    assert org.primary_admin_user_id is not None
    return ProvisionEnterpriseResponse(
        org_id=org.id,
        org_name=org.name,
        slug=org.slug,
        primary_admin_user_id=org.primary_admin_user_id,
        is_enterprise=True,
    )


@router.post("/applications/{application_id}/reject", status_code=204)
async def reject(
    application_id: UUID,
    body: RejectApplicationRequest,
    db: AsyncSession = Depends(get_db),
    ops: str = Depends(require_ops),
) -> None:
    await ent.reject_application(db, application_id, reviewed_by=body.reviewed_by or ops)
    await db.commit()
