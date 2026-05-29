"""Backfill companies + run enrichment for existing contacts."""

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.db import async_session_factory
from app.models import capture, company, contact, user  # noqa: F401
from app.models.contact import Contact
from app.modules.m6_enrichment.enrichment_runner import run_company_enrich
from app.modules.m6_enrichment.service import trigger_enrich_for_contact


async def main() -> None:
    async with async_session_factory() as db:
        result = await db.execute(
            select(Contact).where(Contact.deleted_at.is_(None), Contact.company_name.is_not(None))
        )
        contacts = list(result.scalars().all())
        print(f"Found {len(contacts)} contacts with company_name")
        ok = 0
        for row in contacts:
            try:
                should_run = await trigger_enrich_for_contact(db, row, trigger_type="ingest")
                await db.commit()
                await db.refresh(row)
                if should_run and row.company_id:
                    print(f"  Enriching {row.display_name} / {row.company_name} …")
                    await run_company_enrich(
                        db,
                        company_id=row.company_id,
                        user_id=row.user_id,
                        contact_id=row.id,
                        company_name=row.company_name,
                        contact_website=row.website,
                        trigger_type="ingest",
                    )
                print(f"  OK {row.display_name}")
                ok += 1
            except Exception as exc:
                await db.rollback()
                print(f"  FAIL {row.id}: {exc}")
        print(f"Done: {ok}/{len(contacts)}")


if __name__ == "__main__":
    asyncio.run(main())
