import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.modules.m5_search.live_augment import run_live_augment
from app.modules.m5_search.service import execute_search, get_search_query, get_search_status
from app.schemas.search import (
    CreateSearchQueryRequest,
    LiveAugmentRequest,
    SearchQueryResponse,
    SearchStatusResponse,
)

router = APIRouter()


@router.get("/status", response_model=SearchStatusResponse)
async def search_status(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchStatusResponse:
    return await get_search_status(db, user)


@router.post("/queries", response_model=SearchQueryResponse)
async def create_search_query(
    body: CreateSearchQueryRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchQueryResponse:
    return await execute_search(db, user, body)


@router.get("/queries/{query_id}", response_model=SearchQueryResponse)
async def get_query(
    query_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchQueryResponse:
    return await get_search_query(db, user, query_id)


@router.post("/queries/{query_id}/live-augment", response_model=SearchQueryResponse)
async def live_augment_query(
    query_id: uuid.UUID,
    body: LiveAugmentRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchQueryResponse:
    await run_live_augment(db, user, query_id, contact_ids=body.contact_ids)
    return await get_search_query(db, user, query_id)
