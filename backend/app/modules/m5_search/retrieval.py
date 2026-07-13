import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embed_text, vector_literal
from app.ai.schemas.search_rerank import ParsedIntent
from app.core.team import get_team_user_ids
from app.models.company import CompanyEnrichment
from app.models.contact import Contact
from app.models.contact_search_document import ContactSearchDocument
from app.models.public_business_stub import PublicBusinessStub
from app.models.public_directory_document import PublicDirectoryDocument
from app.modules.m5_search.hybrid import (
    PoolRetrievalDebug,
    RetrievalCandidateDebug,
    build_semantic_query,
    rrf_merge,
)


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


@dataclass
class PublicCandidateDoc:
    stub_id: uuid.UUID
    org_id: uuid.UUID
    org_name: str
    display_name: str
    company_name: str
    title: str | None
    responsibility_keywords: list[str]
    product_keywords: list[str]
    external_card_url: str
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


TRGM_MIN_SCORE = 0.05
WIDENED_POOL_LIMIT = 50


def _trgm_query_strings(intent: ParsedIntent, raw_query: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in (raw_query.strip(), build_retrieval_query(intent, raw_query)):
        key = q.lower()
        if q and key not in seen:
            seen.add(key)
            out.append(q)
    for term in (
        intent.products
        + intent.roles
        + intent.keywords
        + intent.hard_products
        + intent.hard_roles
        + intent.hard_companies
    ):
        t = term.strip()
        key = t.lower()
        if len(t) >= 2 and key not in seen:
            seen.add(key)
            out.append(t)
    return out


async def _private_ts_ids(
    db: AsyncSession, user_ids: list[uuid.UUID], built: str, lim: int
) -> list[uuid.UUID]:
    ts_sql = text(
        """
        SELECT csd.contact_id
        FROM contact_search_documents csd
        JOIN contacts c ON c.id = csd.contact_id
        WHERE csd.user_id = ANY(:user_ids)
          AND c.deleted_at IS NULL
          AND csd.search_vector @@ websearch_to_tsquery('simple', :q)
        ORDER BY ts_rank(csd.search_vector, websearch_to_tsquery('simple', :q)) DESC
        LIMIT :lim
        """
    )
    rows = (await db.execute(ts_sql, {"user_ids": user_ids, "q": built, "lim": lim})).all()
    return [r[0] for r in rows]


async def _private_trgm_ids(
    db: AsyncSession,
    user_ids: list[uuid.UUID],
    intent: ParsedIntent,
    query_text: str,
    lim: int,
    seed_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    if len(seed_ids) >= 5:
        return []
    trgm_sql = text(
        """
        SELECT csd.contact_id
        FROM contact_search_documents csd
        JOIN contacts c ON c.id = csd.contact_id
        WHERE csd.user_id = ANY(:user_ids)
          AND c.deleted_at IS NULL
          AND similarity(csd.search_text, :q) > :min_score
        ORDER BY similarity(csd.search_text, :q) DESC
        LIMIT :lim
        """
    )
    best: list[uuid.UUID] = list(seed_ids)
    seen = set(seed_ids)
    for q in _trgm_query_strings(intent, query_text):
        for row in (
            await db.execute(
                trgm_sql,
                {"user_ids": user_ids, "q": q, "lim": lim, "min_score": TRGM_MIN_SCORE},
            )
        ).all():
            cid = row[0]
            if cid not in seen:
                seen.add(cid)
                best.append(cid)
    return best[:lim]


async def _private_vector_ids(
    db: AsyncSession, user_ids: list[uuid.UUID], query_vec: str, lim: int
) -> list[uuid.UUID]:
    vec_sql = text(
        """
        SELECT csd.contact_id
        FROM contact_search_documents csd
        JOIN contacts c ON c.id = csd.contact_id
        WHERE csd.user_id = ANY(:user_ids)
          AND c.deleted_at IS NULL
          AND csd.embedding IS NOT NULL
        ORDER BY csd.embedding <=> CAST(:qvec AS vector)
        LIMIT :lim
        """
    )
    try:
        rows = (await db.execute(vec_sql, {"user_ids": user_ids, "qvec": query_vec, "lim": lim})).all()
        return [r[0] for r in rows]
    except Exception:
        return []


async def _public_ts_ids(db: AsyncSession, built: str, lim: int) -> list[uuid.UUID]:
    ts_sql = text(
        """
        SELECT pdd.stub_id
        FROM public_directory_documents pdd
        JOIN public_business_stubs s ON s.id = pdd.stub_id
        WHERE s.status = 'published'
          AND pdd.search_vector @@ websearch_to_tsquery('simple', :q)
        ORDER BY ts_rank(pdd.search_vector, websearch_to_tsquery('simple', :q)) DESC
        LIMIT :lim
        """
    )
    rows = (await db.execute(ts_sql, {"q": built, "lim": lim})).all()
    return [r[0] for r in rows]


async def _public_trgm_ids(
    db: AsyncSession,
    intent: ParsedIntent,
    query_text: str,
    lim: int,
    seed_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    if len(seed_ids) >= 5:
        return []
    trgm_sql = text(
        """
        SELECT pdd.stub_id
        FROM public_directory_documents pdd
        JOIN public_business_stubs s ON s.id = pdd.stub_id
        WHERE s.status = 'published'
          AND similarity(pdd.search_text, :q) > :min_score
        ORDER BY similarity(pdd.search_text, :q) DESC
        LIMIT :lim
        """
    )
    best: list[uuid.UUID] = list(seed_ids)
    seen = set(seed_ids)
    for q in _trgm_query_strings(intent, query_text):
        for row in (
            await db.execute(trgm_sql, {"q": q, "lim": lim, "min_score": TRGM_MIN_SCORE})
        ).all():
            sid = row[0]
            if sid not in seen:
                seen.add(sid)
                best.append(sid)
    return best[:lim]


async def _public_vector_ids(db: AsyncSession, query_vec: str, lim: int) -> list[uuid.UUID]:
    vec_sql = text(
        """
        SELECT pdd.stub_id
        FROM public_directory_documents pdd
        JOIN public_business_stubs s ON s.id = pdd.stub_id
        WHERE s.status = 'published'
          AND pdd.embedding IS NOT NULL
        ORDER BY pdd.embedding <=> CAST(:qvec AS vector)
        LIMIT :lim
        """
    )
    try:
        rows = (await db.execute(vec_sql, {"qvec": query_vec, "lim": lim})).all()
        return [r[0] for r in rows]
    except Exception:
        return []


async def _query_embedding(intent: ParsedIntent, query_text: str) -> str | None:
    from app.core.config import get_settings

    if not get_settings().search_embedding_enabled:
        return None
    vec = await embed_text(build_semantic_query(intent, query_text))
    if not vec:
        return None
    return vector_literal(vec)


async def retrieve_candidates(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query_text: str,
    intent: ParsedIntent,
    limit: int | None = None,
) -> tuple[list[CandidateDoc], PoolRetrievalDebug]:
    from app.core.config import get_settings

    settings = get_settings()
    lim = limit if limit is not None else settings.search_retrieval_limit
    built = build_retrieval_query(intent, query_text)
    semantic = build_semantic_query(intent, query_text)

    user_ids = await get_team_user_ids(db, user_id)

    ts_ids = await _private_ts_ids(db, user_ids, built, lim)
    trgm_ids = await _private_trgm_ids(db, user_ids, intent, query_text, lim, ts_ids)
    vector_ids: list[uuid.UUID] = []
    qvec = await _query_embedding(intent, query_text)
    if qvec:
        vector_ids = await _private_vector_ids(db, user_ids, qvec, lim)

    merged = rrf_merge([ts_ids, trgm_ids, vector_ids], k=settings.search_hybrid_rrf_k)
    widened = False

    if not merged:
        rescue_sql = text(
            """
            SELECT csd.contact_id, csd.search_text
            FROM contact_search_documents csd
            JOIN contacts c ON c.id = csd.contact_id
            WHERE csd.user_id = ANY(:user_ids)
              AND c.deleted_at IS NULL
            LIMIT :lim
            """
        )
        rows = list(
            (await db.execute(rescue_sql, {"user_ids": user_ids, "lim": min(lim, WIDENED_POOL_LIMIT)})).all()
        )
        widened = bool(rows)
        merged = [(row[0], 0.0) for row in rows]
        search_text_map = {row[0]: row[1] for row in rows}
    else:
        merged = merged[:lim]
        search_text_map = {}

    out: list[CandidateDoc] = []
    for contact_id, rrf_score in merged:
        if contact_id in search_text_map:
            search_text = search_text_map[contact_id]
        else:
            row = (
                await db.execute(
                    text(
                        "SELECT search_text FROM contact_search_documents WHERE contact_id = :id"
                    ),
                    {"id": contact_id},
                )
            ).first()
            if not row:
                continue
            search_text = row[0]

        contact = await db.get(Contact, contact_id)
        if not contact:
            continue
        products, conf = await _products_for(db, contact.company_id)
        score = 0.0 if widened else float(rrf_score)
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
                search_text=search_text,
                retrieval_score=score,
            )
        )
    ts_set = set(ts_ids)
    debug = PoolRetrievalDebug(
        pool="private",
        lexical_query=built,
        semantic_query=semantic,
        ts_hits=len(ts_ids),
        trgm_extra_hits=len([cid for cid in trgm_ids if cid not in ts_set]),
        vector_hits=len(vector_ids),
        widened=widened,
        top_candidates=[
            RetrievalCandidateDebug(
                id=str(c.contact_id),
                label=c.display_name or c.company_name or str(c.contact_id)[:8],
                retrieval_score=c.retrieval_score,
            )
            for c in out[:10]
        ],
    )
    return out, debug


async def retrieve_public_candidates(
    db: AsyncSession,
    *,
    query_text: str,
    intent: ParsedIntent,
    limit: int | None = None,
) -> tuple[list[PublicCandidateDoc], PoolRetrievalDebug]:
    from app.core.config import get_settings

    settings = get_settings()
    lim = limit if limit is not None else settings.search_retrieval_limit
    built = build_retrieval_query(intent, query_text)
    semantic = build_semantic_query(intent, query_text)

    ts_ids = await _public_ts_ids(db, built, lim)
    trgm_ids = await _public_trgm_ids(db, intent, query_text, lim, ts_ids)
    vector_ids: list[uuid.UUID] = []
    qvec = await _query_embedding(intent, query_text)
    if qvec:
        vector_ids = await _public_vector_ids(db, qvec, lim)

    merged = rrf_merge([ts_ids, trgm_ids, vector_ids], k=settings.search_hybrid_rrf_k)
    widened = False

    if not merged:
        rescue_sql = text(
            """
            SELECT pdd.stub_id, pdd.search_text,
                   s.org_id, s.display_name, s.company_name, s.title,
                   s.responsibility_keywords, s.product_keywords, s.external_card_url,
                   o.name AS org_name
            FROM public_directory_documents pdd
            JOIN public_business_stubs s ON s.id = pdd.stub_id
            JOIN organizations o ON o.id = s.org_id
            WHERE s.status = 'published'
            LIMIT :lim
            """
        )
        rows = list((await db.execute(rescue_sql, {"lim": min(lim, WIDENED_POOL_LIMIT)})).all())
        widened = bool(rows)
        merged = [(row.stub_id, 0.0) for row in rows]
        stub_rows = {row.stub_id: row for row in rows}
    else:
        merged = merged[:lim]
        stub_rows = {}

    out: list[PublicCandidateDoc] = []
    for stub_id, rrf_score in merged:
        if stub_id in stub_rows:
            row = stub_rows[stub_id]
        else:
            row = (
                await db.execute(
                    text(
                        """
                        SELECT pdd.search_text,
                               s.org_id, s.display_name, s.company_name, s.title,
                               s.responsibility_keywords, s.product_keywords, s.external_card_url,
                               o.name AS org_name
                        FROM public_directory_documents pdd
                        JOIN public_business_stubs s ON s.id = pdd.stub_id
                        JOIN organizations o ON o.id = s.org_id
                        WHERE pdd.stub_id = :id AND s.status = 'published'
                        """
                    ),
                    {"id": stub_id},
                )
            ).first()
            if not row:
                continue

        score = 0.0 if widened else float(rrf_score)
        out.append(
            PublicCandidateDoc(
                stub_id=stub_id,
                org_id=row.org_id,
                org_name=row.org_name,
                display_name=row.display_name,
                company_name=row.company_name,
                title=row.title,
                responsibility_keywords=list(row.responsibility_keywords or []),
                product_keywords=list(row.product_keywords or []),
                external_card_url=row.external_card_url,
                search_text=row.search_text,
                retrieval_score=score,
            )
        )
    ts_set = set(ts_ids)
    debug = PoolRetrievalDebug(
        pool="public",
        lexical_query=built,
        semantic_query=semantic,
        ts_hits=len(ts_ids),
        trgm_extra_hits=len([sid for sid in trgm_ids if sid not in ts_set]),
        vector_hits=len(vector_ids),
        widened=widened,
        top_candidates=[
            RetrievalCandidateDebug(
                id=str(c.stub_id),
                label=c.display_name or c.company_name or str(c.stub_id)[:8],
                retrieval_score=c.retrieval_score,
            )
            for c in out[:10]
        ],
    )
    return out, debug


async def count_public_published(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(PublicDirectoryDocument)
        .join(PublicBusinessStub, PublicBusinessStub.id == PublicDirectoryDocument.stub_id)
        .where(PublicBusinessStub.status == "published")
    )
    return int(result.scalar_one())


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
    team_ids = await get_team_user_ids(db, user_id)
    result = await db.execute(
        select(func.count())
        .select_from(ContactSearchDocument)
        .join(Contact, Contact.id == ContactSearchDocument.contact_id)
        .where(
            ContactSearchDocument.user_id.in_(team_ids),
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
        "retrieval_score": c.retrieval_score,
    }


def public_candidate_to_dict(c: PublicCandidateDoc) -> dict:
    scope = " ".join(c.responsibility_keywords)
    return {
        "contact_id": str(c.stub_id),
        "display_name": c.display_name,
        "company_name": c.company_name,
        "title": c.title,
        "responsibility_scope": scope,
        "responsibility_confidence": 0.9,
        "source_label": f"公開商務 · {c.org_name}",
        "review_status": "confirmed",
        "company_products": c.product_keywords,
        "products_confidence": 0.9,
        "search_text": c.search_text,
        "retrieval_score": c.retrieval_score,
    }


def public_to_candidate_doc(c: PublicCandidateDoc) -> CandidateDoc:
    return CandidateDoc(
        contact_id=c.stub_id,
        display_name=c.display_name,
        company_name=c.company_name,
        title=c.title,
        responsibility_scope=" ".join(c.responsibility_keywords),
        responsibility_confidence=0.9,
        source_label=f"公開商務 · {c.org_name}",
        review_status="confirmed",
        phones=[],
        emails=[],
        image_url=None,
        company_products=c.product_keywords,
        products_confidence=0.9,
        search_text=c.search_text,
        retrieval_score=c.retrieval_score,
    )
