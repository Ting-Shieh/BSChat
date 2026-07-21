"""F1 in-app notifications service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import UserNotification
from app.models.user import User


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    kind: str,
    title: str,
    body: str | None,
    payload: dict[str, Any],
) -> UserNotification:
    row = UserNotification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        payload=payload,
    )
    db.add(row)
    await db.flush()
    return row


async def list_my_notifications(
    db: AsyncSession,
    user: User,
    *,
    unread_only: bool = False,
    limit: int = 50,
) -> list[UserNotification]:
    q = select(UserNotification).where(UserNotification.user_id == user.id)
    if unread_only:
        q = q.where(UserNotification.read_at.is_(None))
    q = q.order_by(UserNotification.created_at.desc()).limit(limit)
    return list((await db.execute(q)).scalars().all())


async def unread_count(db: AsyncSession, user: User) -> int:
    rows = await list_my_notifications(db, user, unread_only=True, limit=200)
    return len(rows)


async def get_owned_notification(
    db: AsyncSession, user: User, notification_id: uuid.UUID
) -> UserNotification:
    row = (
        await db.execute(
            select(UserNotification).where(
                UserNotification.id == notification_id,
                UserNotification.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOTIFICATION_NOT_FOUND")
    return row


async def mark_read(db: AsyncSession, user: User, notification_id: uuid.UUID) -> UserNotification:
    row = await get_owned_notification(db, user, notification_id)
    if row.read_at is None:
        row.read_at = datetime.now(UTC)
        await db.flush()
    return row
