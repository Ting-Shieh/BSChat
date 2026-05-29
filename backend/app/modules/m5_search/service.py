import time
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import reset_search_cache_quota_if_needed
from app.ai.pipelines.search_intent import parse_intent
from app.ai.pipelines.search_rerank import rerank_contacts
from app.models.contact import Contact
from app.models.search import SearchQuery, SearchResult
from app.models.user import User, UserEntitlement
from app.modules.m5_search.constraints import filter_rerank_results, has_hard_constraints
from app.modules.m5_search.retrieval import CandidateDoc, candidate_to_dict, count_indexed, retrieve_candidates
from app.modules.m5_search.sample_queries import pick_sample_queries
from app.modules.m5_search.validate import apply_confirmed_boost, validate_rerank_item
from app.schemas.search import (
    ContactPreviewDTO,
    CreateSearchQueryRequest,
    MatchSourceDTO,
    SearchEmptyStateDTO,
    SearchQueryResponse,
    SearchQuotasDTO,
    SearchResultItemDTO,
    SearchStatusResponse,
)

async def get_search_status(db: AsyncSession, user: User) -> SearchStatusResponse:
    indexed = await count_indexed(db, user.id)
    ent = user.entitlement
    await reset_search_cache_quota_if_needed(db, ent)
    return SearchStatusResponse(
        indexed_count=indexed,
        can_search=indexed > 0,
        sample_queries=await pick_sample_queries(db, user),
        quotas=SearchQuotasDTO(
            search_cache_remaining_today=max(0, ent.search_cache_daily_quota - ent.search_cache_used_today),
            live_augment_remaining_month=max(
                0, ent.live_augment_monthly_quota - ent.live_augment_used_this_month
            ),
        ),
    )


async def _check_and_increment_quota(db: AsyncSession, user: User) -> None:
    ent = user.entitlement
    await reset_search_cache_quota_if_needed(db, ent)
    if ent.search_cache_used_today >= ent.search_cache_daily_quota:
        raise HTTPException(status_code=429, detail="SEARCH_QUOTA_EXCEEDED")
    ent.search_cache_used_today += 1
    await db.flush()


async def _had_successful_search(db: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(func.count())
        .select_from(SearchQuery)
        .where(SearchQuery.user_id == user_id, SearchQuery.status == "COMPLETED", SearchQuery.result_count > 0)
    )
    return int(result.scalar_one()) > 0


def _preview_from_candidate(c: CandidateDoc) -> ContactPreviewDTO:
    phones = [p.get("value", "") for p in c.phones if isinstance(p, dict) and p.get("value")]
    emails = [e.get("value", "") for e in c.emails if isinstance(e, dict) and e.get("value")]
    return ContactPreviewDTO(
        display_name=c.display_name,
        company_name=c.company_name,
        title=c.title,
        review_status=c.review_status,
        phones=phones[:2],
        emails=emails[:2],
        image_url=c.image_url,
    )


async def execute_search(
    db: AsyncSession,
    user: User,
    body: CreateSearchQueryRequest,
) -> SearchQueryResponse:
    if body.search_scope != "private":
        raise HTTPException(status_code=403, detail="SEARCH_SCOPE_NOT_ALLOWED")

    indexed = await count_indexed(db, user.id)
    if indexed == 0:
        q = SearchQuery(
            user_id=user.id,
            workspace_id=user.workspace.id,
            query_text=body.query_text,
            status="EMPTY",
            result_count=0,
        )
        db.add(q)
        await db.commit()
        await db.refresh(q)
        return SearchQueryResponse(
            query_id=q.id,
            status="EMPTY",
            empty_state=SearchEmptyStateDTO(
                reason="NO_INDEXED_CONTACTS",
                suggestions=["先收錄幾張名片，系統會自動建立搜尋索引"],
                sample_queries=await pick_sample_queries(db, user),
                cta={"action": "capture", "label": "去收錄名片"},
            ),
        )

    await _check_and_increment_quota(db, user)
    started = time.perf_counter()
    intent = await parse_intent(body.query_text)

    query_row = SearchQuery(
        user_id=user.id,
        workspace_id=user.workspace.id,
        query_text=body.query_text,
        parsed_intent=intent.model_dump(),
        status="RETRIEVING",
    )
    db.add(query_row)
    await db.flush()

    candidates = await retrieve_candidates(db, user_id=user.id, query_text=body.query_text, intent=intent)
    candidate_map = {str(c.contact_id): c for c in candidates}

    rerank_resp, degraded = await rerank_contacts(
        body.query_text,
        [candidate_to_dict(c) for c in candidates],
        intent,
    )

    filtered = filter_rerank_results(rerank_resp.results, candidate_map, intent)

    validated = []
    for item in filtered:
        cand = candidate_map.get(item.contact_id)
        if cand and validate_rerank_item(item, cand):
            validated.append((item, cand))

    if not validated and candidates and not has_hard_constraints(intent):
        best_retrieval = max((c.retrieval_score or 0) for c in candidates)
        if best_retrieval >= 0.12:
            degraded = True
            for c in candidates[:5]:
                validated.append(
                    (
                        type("R", (), {
                            "contact_id": str(c.contact_id),
                            "match_score": c.retrieval_score or 0.4,
                            "match_reason": f"文字相關：{c.display_name} · {c.company_name or ''}",
                            "match_sources": [],
                        })(),
                        c,
                    )
                )

    latency_ms = int((time.perf_counter() - started) * 1000)

    if not validated:
        query_row.status = "EMPTY"
        query_row.result_count = 0
        query_row.latency_ms = latency_ms
        query_row.degraded = degraded
        reason = "LOW_INDEX_COUNT" if indexed < 3 else "NO_MATCH"
        suggestions = (
            ["再多收錄幾張名片，搜尋會更準", "試試以公司名稱或職稱描述你要找的人"]
            if reason == "LOW_INDEX_COUNT"
            else ["試試更通用的關鍵字，例如公司產品或職稱", "換個說法，例如「誰做工業電腦的？」"]
        )
        stored = dict(query_row.parsed_intent or {})
        stored["empty_reason"] = reason
        query_row.parsed_intent = stored
        await db.commit()
        return SearchQueryResponse(
            query_id=query_row.id,
            status="EMPTY",
            latency_ms=latency_ms,
            degraded=degraded,
            empty_state=SearchEmptyStateDTO(
                reason=reason,
                suggestions=suggestions,
                sample_queries=await pick_sample_queries(db, user),
                cta={"action": "capture", "label": "去收錄名片"} if indexed < 3 else None,
            ),
        )

    had_prior = await _had_successful_search(db, user.id)
    results_dto: list[SearchResultItemDTO] = []

    for rank, (item, cand) in enumerate(validated[:10], start=1):
        score = apply_confirmed_boost(float(item.match_score), cand.review_status)
        sources = [
            MatchSourceDTO(field=s.field, value=s.value, confidence=s.confidence)
            for s in (getattr(item, "match_sources", None) or [])
        ]
        db.add(
            SearchResult(
                query_id=query_row.id,
                contact_id=cand.contact_id,
                rank=rank,
                match_score=score,
                match_reason=item.match_reason,
                match_sources=[s.model_dump() for s in sources],
            )
        )
        results_dto.append(
            SearchResultItemDTO(
                contact_id=cand.contact_id,
                rank=rank,
                match_score=score,
                match_reason=item.match_reason,
                match_sources=sources,
                contact_preview=_preview_from_candidate(cand),
            )
        )

    query_row.status = "COMPLETED"
    query_row.result_count = len(results_dto)
    query_row.latency_ms = latency_ms
    query_row.degraded = degraded
    await db.commit()

    aha = not had_prior and len(results_dto) > 0
    return SearchQueryResponse(
        query_id=query_row.id,
        status="COMPLETED",
        result_count=len(results_dto),
        latency_ms=latency_ms,
        degraded=degraded,
        aha_moment=aha,
        results=results_dto,
    )


async def get_search_query(db: AsyncSession, user: User, query_id: uuid.UUID) -> SearchQueryResponse:
    result = await db.execute(
        select(SearchQuery).where(SearchQuery.id == query_id, SearchQuery.user_id == user.id)
    )
    query_row = result.scalar_one_or_none()
    if not query_row:
        raise HTTPException(status_code=404, detail="Query not found")

    if query_row.status == "EMPTY":
        stored = query_row.parsed_intent or {}
        reason = stored.get("empty_reason", "NO_MATCH")
        suggestions = (
            ["再多收錄幾張名片，搜尋會更準", "試試以公司名稱或職稱描述你要找的人"]
            if reason == "LOW_INDEX_COUNT"
            else ["試試更通用的關鍵字，例如公司產品或職稱", "換個說法，例如「誰做工業電腦的？」"]
        )
        return SearchQueryResponse(
            query_id=query_row.id,
            status="EMPTY",
            latency_ms=query_row.latency_ms,
            empty_state=SearchEmptyStateDTO(
                reason=reason,
                suggestions=suggestions,
                sample_queries=await pick_sample_queries(db, user),
            ),
        )

    res = await db.execute(
        select(SearchResult).where(SearchResult.query_id == query_id).order_by(SearchResult.rank)
    )
    rows = list(res.scalars().all())
    items: list[SearchResultItemDTO] = []
    for row in rows:
        contact = await db.get(Contact, row.contact_id)
        if not contact:
            continue
        from app.modules.m5_search.retrieval import _products_for

        products, conf = await _products_for(db, contact.company_id)
        cand = CandidateDoc(
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
            search_text=contact.search_text or "",
            retrieval_score=row.match_score,
        )
        items.append(
            SearchResultItemDTO(
                contact_id=row.contact_id,
                rank=row.rank,
                match_score=row.match_score,
                match_reason=row.match_reason,
                match_sources=[MatchSourceDTO(**s) for s in row.match_sources or []],
                contact_preview=_preview_from_candidate(cand),
            )
        )

    return SearchQueryResponse(
        query_id=query_row.id,
        status=query_row.status,
        result_count=query_row.result_count,
        latency_ms=query_row.latency_ms,
        degraded=query_row.degraded,
        results=items,
    )
