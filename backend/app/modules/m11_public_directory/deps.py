"""M11 org admin authorization."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.models.organization import OrgMember, Organization


async def require_org_admin(
    org_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Organization:
    if user.entitlement.plan_tier != "enterprise":
        raise HTTPException(status_code=403, detail="ENTERPRISE_REQUIRED")

    result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(Organization.id == org_id, OrgMember.user_id == user.id, OrgMember.role == "admin")
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=403, detail="ORG_ACCESS_DENIED")
    return org


OrgAdmin = Annotated[Organization, Depends(require_org_admin)]
