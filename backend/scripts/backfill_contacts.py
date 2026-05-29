"""Backfill contacts from existing handoff_events."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.db import async_session_factory
from app.models import capture, contact, user  # noqa: F401 — register ORM mappers
from app.models.capture import HandoffEvent
from app.modules.m3_contacts.upsert import upsert_from_payload


async def main() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(HandoffEvent).order_by(HandoffEvent.created_at))
        events = list(result.scalars().all())
        print(f"Found {len(events)} handoff events")
        ok = 0
        for event in events:
            try:
                contact_row = await upsert_from_payload(db, event.payload)
                print(f"  OK {event.raw_card_id} -> {contact_row.display_name}")
                ok += 1
            except Exception as exc:
                await db.rollback()
                print(f"  FAIL {event.raw_card_id}: {exc}")
        print(f"Done: {ok}/{len(events)}")


if __name__ == "__main__":
    asyncio.run(main())
