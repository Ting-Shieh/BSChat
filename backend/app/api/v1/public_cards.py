"""Public e-card read API (no auth) — only published / AI-recommendable cards."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.modules.m11_public_directory.service import get_published_public_card
from app.schemas.org import PublicCardResponse

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/cards/{stub_id}", response_model=PublicCardResponse)
async def get_public_card(
    stub_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicCardResponse:
    row = await get_published_public_card(db, stub_id)
    if row is None:
        raise HTTPException(status_code=404, detail="CARD_NOT_FOUND")
    stub, org = row
    return PublicCardResponse(
        id=stub.id,
        display_name=stub.display_name,
        company_name=stub.company_name,
        title=stub.title,
        one_line_blurb=stub.one_line_blurb,
        avatar_url=stub.avatar_url,
        responsibility_keywords=list(stub.responsibility_keywords or []),
        product_keywords=list(stub.product_keywords or []),
        external_card_url=stub.external_card_url,
        org_name=org.name,
    )
