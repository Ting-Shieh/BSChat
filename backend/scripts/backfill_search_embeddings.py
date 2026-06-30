#!/usr/bin/env python3
"""Backfill search index embeddings (Pool A + Pool B). Run after migration 014."""

import asyncio

from sqlalchemy import select, text

from app.ai.embeddings import embed_text, vector_literal
from app.core.db import async_session_factory
from app.models.contact_search_document import ContactSearchDocument
from app.models.public_directory_document import PublicDirectoryDocument


async def _backfill_contact_docs() -> int:
    count = 0
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(ContactSearchDocument.contact_id, ContactSearchDocument.search_text).where(
                    ContactSearchDocument.embedding.is_(None)
                )
            )
        ).all()
        for contact_id, search_text in rows:
            vec = await embed_text(search_text)
            if not vec:
                continue
            await db.execute(
                text(
                    """
                    UPDATE contact_search_documents
                    SET embedding = CAST(:embedding AS vector)
                    WHERE contact_id = :contact_id
                    """
                ),
                {"contact_id": contact_id, "embedding": vector_literal(vec)},
            )
            count += 1
        await db.commit()
    return count


async def _backfill_public_docs() -> int:
    count = 0
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(PublicDirectoryDocument.stub_id, PublicDirectoryDocument.search_text).where(
                    PublicDirectoryDocument.embedding.is_(None)
                )
            )
        ).all()
        for stub_id, search_text in rows:
            vec = await embed_text(search_text)
            if not vec:
                continue
            await db.execute(
                text(
                    """
                    UPDATE public_directory_documents
                    SET embedding = CAST(:embedding AS vector)
                    WHERE stub_id = :stub_id
                    """
                ),
                {"stub_id": stub_id, "embedding": vector_literal(vec)},
            )
            count += 1
        await db.commit()
    return count


async def main() -> None:
    private_n = await _backfill_contact_docs()
    public_n = await _backfill_public_docs()
    print(f"Backfilled embeddings: private={private_n}, public={public_n}")


if __name__ == "__main__":
    asyncio.run(main())
