"""Backfill contact_search_documents for existing contacts."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.db import async_session_factory
from app.models import capture, company, contact, contact_search_document, search, user  # noqa: F401
from app.models.contact import Contact
from app.modules.m3_contacts.index_builder import index_contact


async def main() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(Contact).where(Contact.deleted_at.is_(None)))
        contacts = list(result.scalars().all())
        print(f"Indexing {len(contacts)} contacts")
        ok = 0
        for row in contacts:
            try:
                await index_contact(db, row.id)
                print(f"  OK {row.display_name}")
                ok += 1
            except Exception as exc:
                await db.rollback()
                print(f"  FAIL {row.id}: {exc}")
        print(f"Done: {ok}/{len(contacts)}")


if __name__ == "__main__":
    asyncio.run(main())
