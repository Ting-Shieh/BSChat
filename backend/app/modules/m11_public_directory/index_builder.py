"""Build and upsert public_directory_documents (Pool B index)."""

import uuid

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embed_text, vector_literal
from app.models.public_business_stub import PublicBusinessStub
from app.models.public_directory_document import PublicDirectoryDocument, content_hash_for


def build_search_text(stub: PublicBusinessStub) -> str:
    resp = " ".join(str(k) for k in (stub.responsibility_keywords or []))
    products = " ".join(str(k) for k in (stub.product_keywords or []))
    parts = [
        stub.display_name or "",
        stub.company_name or "",
        stub.title or "",
        resp,
        products,
    ]
    return " | ".join(p for p in parts if p.strip())


async def index_stub(db: AsyncSession, stub_id: uuid.UUID) -> None:
    result = await db.execute(select(PublicBusinessStub).where(PublicBusinessStub.id == stub_id))
    stub = result.scalar_one_or_none()
    if not stub or stub.status != "published":
        return

    search_text = build_search_text(stub)
    content_hash = content_hash_for(search_text)

    doc_result = await db.execute(
        select(PublicDirectoryDocument).where(PublicDirectoryDocument.stub_id == stub_id)
    )
    doc = doc_result.scalar_one_or_none()
    if doc and doc.content_hash == content_hash and doc.embedding is not None:
        await db.commit()
        return

    if doc is None:
        doc = PublicDirectoryDocument(
            stub_id=stub.id,
            org_id=stub.org_id,
            search_text=search_text,
            content_hash=content_hash,
        )
        db.add(doc)
    else:
        doc.search_text = search_text
        doc.content_hash = content_hash

    await db.flush()
    embedding_vec = await embed_text(search_text)
    try:
        if embedding_vec:
            await db.execute(
                text(
                    """
                    UPDATE public_directory_documents
                    SET search_vector = to_tsvector('simple', search_text),
                        embedding = CAST(:embedding AS vector),
                        indexed_at = NOW()
                    WHERE stub_id = :stub_id
                    """
                ),
                {"stub_id": stub.id, "embedding": vector_literal(embedding_vec)},
            )
        else:
            raise RuntimeError("skip embedding")
    except Exception:
        await db.execute(
            text(
                """
                UPDATE public_directory_documents
                SET search_vector = to_tsvector('simple', search_text),
                    indexed_at = NOW()
                WHERE stub_id = :stub_id
                """
            ),
            {"stub_id": stub.id},
        )
    await db.commit()


async def unindex_stub(db: AsyncSession, stub_id: uuid.UUID) -> None:
    await db.execute(delete(PublicDirectoryDocument).where(PublicDirectoryDocument.stub_id == stub_id))
    await db.commit()
