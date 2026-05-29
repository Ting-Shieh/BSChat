"""Seed dev user for local development."""

import asyncio
import uuid

from sqlalchemy import select

from app.core.db import async_session_factory
from app.models.user import User, UserEntitlement, Workspace

DEV_EMAIL = "dev@example.com"
DEV_NAME = "Dev User"


async def seed() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == DEV_EMAIL))
        if result.scalar_one_or_none():
            print(f"Dev user already exists: {DEV_EMAIL}")
            return

        user = User(id=uuid.uuid4(), email=DEV_EMAIL, display_name=DEV_NAME)
        db.add(user)
        await db.flush()
        db.add(Workspace(owner_user_id=user.id, name="Personal"))
        db.add(UserEntitlement(user_id=user.id))
        await db.commit()
        print(f"Created dev user: {DEV_EMAIL}")


if __name__ == "__main__":
    asyncio.run(seed())
