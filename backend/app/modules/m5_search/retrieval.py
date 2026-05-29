import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas.search_rerank import ParsedIntent
from app.models.company import CompanyEnrichment
from app.models.contact import Contact
from app.models.contact_search_document import ContactSearchDocument


@dataclass
class CandidateDoc:
    contact_id: uuid.UUID
    display_name: str | None
    company_name: str | None
    title: str | None
    responsibility_scope: str | None
    responsibility_confidence: float | None
    source_label: str | None
    review_status: str
    phones: list
    emails: list
    image_url: str | None
    company_products: list[str]
    products_confidence: float | None
    search_text: str
    retrieval_score: float


def build_retrieval_query(intent: ParsedIntent, raw_query: str) -> str:
    parts = (
        intent.products
        + intent.roles
        + intent.hard_products
        + intent.hard_roles
        + intent.hard_companies
        + intent.keywords
    )
    if not parts:
        return raw_query
    return " ".join(parts)


async def retrieve_candidates(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query_text: str,
    intent: ParsedIntent,
    limit: int = 50,
) -> list[CandidateDoc]:
    built = build_retrieval_query(intent, query_text)

    ts_sql = text(
        """
        SELECT csd.contact_id, csd.search_text,
               ts_rank(csd.search_vector, websearch_to_tsquery('simple', :q)) AS score
        FROM contact_search_documents csd
        JOIN contacts c ON c.id = csd.contact_id
        WHERE csd.user_id = :user_id
          AND c.deleted_at IS NULL
          AND csd.search_vector @@ websearch_to_tsquery('simple', :q)
        ORDER BY score DESC
        LIMIT :lim
        """
    )
    rows = (
        await db.execute(ts_sql, {"user_id": user_id, "q": built, "lim": limit})
    ).all()

    if len(rows) < 5:
        trgm_sql = text(
            """
            SELECT csd.contact_id, csd.search_text,
                   similarity(csd.search_text, :q) AS score
            FROM contact_search_documents csd
            JOIN contacts c ON c.id = csd.contact_id
            WHERE csd.user_id = :user_id
              AND c.deleted_at IS NULL
              AND similarity(csd.search_text, :q) > 0.08
            ORDER BY score DESC
            LIMIT :lim
            """
        )
        trgm_rows = (
            await db.execute(trgm_sql, {"user_id": user_id, "q": query_text, "lim": limit})
        ).all()
        seen = {r.contact_id for r in rows}
        for r in trgm_rows:
            if r.contact_id not in seen:
                rows.append(r)
                seen.add(r.contact_id)

    if not rows:
        fallback = await db.execute(
            select(ContactSearchDocument.contact_id, ContactSearchDocument.search_text)
            .join(Contact, Contact.id == ContactSearchDocument.contact_id)
            .where(ContactSearchDocument.user_id == user_id, Contact.deleted_at.is_(None))
            .limit(limit)
        )
        rows = [(r.contact_id, r.search_text, 0.1) for r in fallback.all()]

    out: list[CandidateDoc] = []
    for row in rows:
        contact_id = row[0]
        contact = await db.get(Contact, contact_id)
        if not contact:
            continue
        products, conf = await _products_for(db, contact.company_id)
        out.append(
            CandidateDoc(
                contact_id=contact.id,
                display_name=contact.display_name,
                company_name=contact.company_name,
                title=contact.title,
                responsibility_scope=contact.responsibility_scope,
                responsibility_confidence=contact.responsibility_confidence,
                source_label=contact.source_label,
                review_status=contact.review_status,
                phones=contact.phones or [],
                emails=contact.emails or [],
                image_url=contact.image_url,
                company_products=products,
                products_confidence=conf,
                search_text=row[1],
                retrieval_score=float(row[2] if len(row) > 2 else 0),
            )
        )
    return out


async def _products_for(db: AsyncSession, company_id: uuid.UUID | None) -> tuple[list[str], float | None]:
    if not company_id:
        return [], None
    result = await db.execute(
        select(CompanyEnrichment)
        .where(CompanyEnrichment.company_id == company_id)
        .order_by(CompanyEnrichment.enrich_version.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return [], None
    return list(row.main_products or []), row.overall_confidence


async def count_indexed(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Pool A: active contacts with a search index (DDR-72)."""
    result = await db.execute(
        select(func.count())
        .select_from(ContactSearchDocument)
        .join(Contact, Contact.id == ContactSearchDocument.contact_id)
        .where(
            ContactSearchDocument.user_id == user_id,
            Contact.deleted_at.is_(None),
        )
    )
    return int(result.scalar_one())


def candidate_to_dict(c: CandidateDoc) -> dict:
    return {
        "contact_id": str(c.contact_id),
        "display_name": c.display_name,
        "company_name": c.company_name,
        "title": c.title,
        "responsibility_scope": c.responsibility_scope,
        "responsibility_confidence": c.responsibility_confidence,
        "source_label": c.source_label,
        "review_status": c.review_status,
        "company_products": c.company_products,
        "products_confidence": c.products_confidence,
        "search_text": c.search_text,
    }
