"""Multiturn search sessions (DDR-v4-17)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import SearchQuery, SearchSession
from app.models.user import User

BROWSE_PREVIEW_LIMIT = 3
BROWSE_MORE_LIMIT = 12


def _title_from_query(text: str) -> str:
    t = " ".join((text or "").strip().split())
    return t[:80] if t else "新搜尋"


async def resolve_session_for_query(
    db: AsyncSession,
    user: User,
    *,
    session_id: uuid.UUID | None,
    query_text: str,
) -> SearchSession:
    if session_id is not None:
        session = await db.get(SearchSession, session_id)
        if session is None or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="SEARCH_SESSION_NOT_FOUND")
        session.turn_count = int(session.turn_count or 0) + 1
        session.updated_at = datetime.now(UTC)
        await db.flush()
        return session

    session = SearchSession(
        user_id=user.id,
        workspace_id=user.workspace.id,
        title=_title_from_query(query_text),
        turn_count=1,
        status="active",
    )
    db.add(session)
    await db.flush()
    return session


async def prior_query_texts(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    limit: int = 4,
) -> list[str]:
    result = await db.execute(
        select(SearchQuery.query_text)
        .where(SearchQuery.session_id == session_id)
        .order_by(SearchQuery.created_at.desc())
        .limit(limit)
    )
    texts = [row[0] for row in result.all() if row[0]]
    texts.reverse()
    return texts


def build_effective_query(current: str, priors: list[str]) -> str:
    """Retrieval context: earlier turns + current follow-up."""
    current = (current or "").strip()
    if not priors:
        return current
    prior_block = "；".join(priors[-3:])
    return f"先前需求：{prior_block}。當前追問：{current}"


async def list_sessions(
    db: AsyncSession,
    user: User,
    *,
    limit: int = 30,
) -> list[SearchSession]:
    result = await db.execute(
        select(SearchSession)
        .where(SearchSession.user_id == user.id)
        .order_by(SearchSession.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_session_for_user(
    db: AsyncSession,
    user: User,
    session_id: uuid.UUID,
) -> SearchSession:
    session = await db.get(SearchSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="SEARCH_SESSION_NOT_FOUND")
    return session


async def list_session_queries(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> list[SearchQuery]:
    result = await db.execute(
        select(SearchQuery)
        .where(SearchQuery.session_id == session_id)
        .order_by(SearchQuery.created_at.asc())
    )
    return list(result.scalars().all())
