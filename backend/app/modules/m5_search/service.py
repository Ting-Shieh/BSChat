import time
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import reset_live_augment_quota_if_needed, reset_search_cache_quota_if_needed
from app.core.media_urls import public_media_url
from app.ai.pipelines.search_intent import parse_intent
from app.ai.pipelines.search_rerank import rerank_contacts
from app.models.contact import Contact
from app.models.organization import Organization
from app.models.public_business_stub import PublicBusinessStub
from app.models.search import SearchQuery, SearchResult
from app.models.user import User, UserEntitlement
from app.modules.m5_search.constraints import filter_rerank_results, has_hard_constraints
from app.modules.m5_search.retrieval import (
    CandidateDoc,
    candidate_to_dict,
    count_indexed,
    count_public_published,
    retrieve_candidates,
    retrieve_public_candidates,
)
from app.modules.m5_search.public_search import ALLOWED_SEARCH_SCOPES, can_use_network_scope, rank_public_candidates
from app.modules.m5_search.sample_queries import pick_sample_queries
from app.modules.m5_search.live_augment import should_suggest_live
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
    StubPreviewDTO,
)

async def get_search_status(db: AsyncSession, user: User) -> SearchStatusResponse:
    indexed = await count_indexed(db, user.id)
    public_pool = await count_public_published(db)
    ent = user.entitlement
    await reset_search_cache_quota_if_needed(db, ent)
    await reset_live_augment_quota_if_needed(db, ent)
    can_search = indexed > 0 or (can_use_network_scope(ent.plan_tier) and public_pool > 0)
    return SearchStatusResponse(
        indexed_count=indexed,
        can_search=can_search,
        sample_queries=await pick_sample_queries(db, user),
        public_pool_count=public_pool,
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
        image_url=public_media_url(c.image_url),
    )


def _public_result_dto(rank: int, item, pub, score: float, sources: list[MatchSourceDTO]) -> SearchResultItemDTO:
    reason = item.match_reason
    if "公開商務" not in reason:
        reason = f"{reason}；公開商務 · {pub.org_name}"
    return SearchResultItemDTO(
        rank=rank,
        match_score=score,
        match_reason=reason,
        match_sources=sources,
        source_pool="public_directory",
        stub_id=pub.stub_id,
        publisher_org_id=pub.org_id,
        publisher_org_name=pub.org_name,
        external_card_url=pub.external_card_url,
        stub_preview=StubPreviewDTO(
            display_name=pub.display_name,
            company_name=pub.company_name,
            title=pub.title,
            product_keywords=list(pub.product_keywords or []),
        ),
    )


async def execute_search(
    db: AsyncSession,
    user: User,
    body: CreateSearchQueryRequest,
) -> SearchQueryResponse:
    scope = (body.search_scope or "private").lower()
    if scope not in ALLOWED_SEARCH_SCOPES:
        raise HTTPException(status_code=400, detail="INVALID_SEARCH_SCOPE")
    if scope != "private" and not can_use_network_scope(user.entitlement.plan_tier):
        raise HTTPException(status_code=403, detail="SEARCH_SCOPE_NOT_ALLOWED")

    indexed = await count_indexed(db, user.id)
    public_pool = await count_public_published(db)
    include_private = scope in ("private", "all")
    include_public = scope in ("network", "all")

    if scope == "private" and indexed == 0:
        q = SearchQuery(
            user_id=user.id,
            workspace_id=user.workspace.id,
            query_text=body.query_text,
            search_scope=scope,
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

    if scope == "network" and public_pool == 0:
        q = SearchQuery(
            user_id=user.id,
            workspace_id=user.workspace.id,
            query_text=body.query_text,
            search_scope=scope,
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
                reason="NO_PUBLIC_DIRECTORY",
                suggestions=["平台尚無公開商務身份，請稍後再試"],
                sample_queries=await pick_sample_queries(db, user),
            ),
        )

    if scope == "all" and indexed == 0 and public_pool == 0:
        q = SearchQuery(
            user_id=user.id,
            workspace_id=user.workspace.id,
            query_text=body.query_text,
            search_scope=scope,
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
                suggestions=["先收錄名片，或等平台有更多公開商務身份"],
                sample_queries=await pick_sample_queries(db, user),
                cta={"action": "capture", "label": "去收錄名片"},
            ),
        )

    await _check_and_increment_quota(db, user)
    started = time.perf_counter()
    intent = await parse_intent(body.query_text)
    degraded = False

    query_row = SearchQuery(
        user_id=user.id,
        workspace_id=user.workspace.id,
        query_text=body.query_text,
        parsed_intent=intent.model_dump(),
        search_scope=scope,
        status="RETRIEVING",
    )
    db.add(query_row)
    await db.flush()

    private_validated: list[tuple[object, CandidateDoc]] = []
    if include_private and indexed > 0:
        candidates = await retrieve_candidates(db, user_id=user.id, query_text=body.query_text, intent=intent)
        candidate_map = {str(c.contact_id): c for c in candidates}
        rerank_resp, priv_degraded = await rerank_contacts(
            body.query_text,
            [candidate_to_dict(c) for c in candidates],
            intent,
        )
        degraded = degraded or priv_degraded
        filtered = filter_rerank_results(rerank_resp.results, candidate_map, intent)
        for item in filtered:
            cand = candidate_map.get(item.contact_id)
            if cand and validate_rerank_item(item, cand):
                private_validated.append((item, cand))
        if not private_validated and candidates and not has_hard_constraints(intent):
            best_retrieval = max((c.retrieval_score or 0) for c in candidates)
            if best_retrieval >= 0.12:
                degraded = True
                for c in candidates[:5]:
                    private_validated.append(
                        (
                            type(
                                "R",
                                (),
                                {
                                    "contact_id": str(c.contact_id),
                                    "match_score": c.retrieval_score or 0.4,
                                    "match_reason": f"文字相關：{c.display_name} · {c.company_name or ''}",
                                    "match_sources": [],
                                },
                            )(),
                            c,
                        )
                    )

    public_validated: list[tuple[object, object]] = []
    if include_public and public_pool > 0:
        public_candidates = await retrieve_public_candidates(db, query_text=body.query_text, intent=intent)
        pub_ranked, pub_degraded = await rank_public_candidates(body.query_text, public_candidates, intent)
        public_validated = pub_ranked
        degraded = degraded or pub_degraded

    combined: list[tuple[str, float, object, object]] = []
    for item, cand in private_validated:
        score = apply_confirmed_boost(float(item.match_score), cand.review_status)
        combined.append(("private", score, item, cand))
    for item, pub in public_validated:
        combined.append(("public", float(item.match_score), item, pub))
    combined.sort(key=lambda x: x[1], reverse=True)
    combined = combined[:10]

    latency_ms = int((time.perf_counter() - started) * 1000)

    if not combined:
        reason = "NO_MATCH"
        if scope == "network":
            reason = "NO_MATCH_PUBLIC"
        elif indexed < 3:
            reason = "LOW_INDEX_COUNT"
        suggestions = (
            ["再多收錄幾張名片，搜尋會更準", "試試以公司名稱或職稱描述你要找的人"]
            if reason == "LOW_INDEX_COUNT"
            else ["試試更通用的關鍵字，例如公司產品或職稱", "換個說法，例如「誰做工業電腦的？」"]
        )
        query_row.status = "EMPTY"
        query_row.result_count = 0
        query_row.latency_ms = latency_ms
        query_row.degraded = degraded
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
                cta={"action": "capture", "label": "去收錄名片"} if indexed < 3 and scope != "network" else None,
            ),
        )

    had_prior = await _had_successful_search(db, user.id)
    results_dto: list[SearchResultItemDTO] = []
    private_ids: list[uuid.UUID] = []

    for rank, (pool, score, item, entity) in enumerate(combined, start=1):
        sources = [
            MatchSourceDTO(field=s.field, value=s.value, confidence=s.confidence)
            for s in (getattr(item, "match_sources", None) or [])
        ]
        if pool == "private":
            cand = entity
            private_ids.append(cand.contact_id)
            db.add(
                SearchResult(
                    query_id=query_row.id,
                    contact_id=cand.contact_id,
                    rank=rank,
                    match_score=score,
                    match_reason=item.match_reason,
                    match_sources=[s.model_dump() for s in sources],
                    source_pool="private_rolodex",
                )
            )
            results_dto.append(
                SearchResultItemDTO(
                    contact_id=cand.contact_id,
                    rank=rank,
                    match_score=score,
                    match_reason=item.match_reason,
                    match_sources=sources,
                    source_pool="private_rolodex",
                    contact_preview=_preview_from_candidate(cand),
                )
            )
        else:
            pub = entity
            db.add(
                SearchResult(
                    query_id=query_row.id,
                    stub_id=pub.stub_id,
                    rank=rank,
                    match_score=score,
                    match_reason=item.match_reason,
                    match_sources=[s.model_dump() for s in sources],
                    source_pool="public_directory",
                )
            )
            results_dto.append(_public_result_dto(rank, item, pub, score, sources))

    query_row.status = "COMPLETED"
    query_row.result_count = len(results_dto)
    query_row.latency_ms = latency_ms
    query_row.degraded = degraded
    query_row.suggest_live = await should_suggest_live(db, user, private_ids) if private_ids else False
    suggest_live_flag = query_row.suggest_live
    await db.commit()

    aha = not had_prior and len(results_dto) > 0
    return SearchQueryResponse(
        query_id=query_row.id,
        status="COMPLETED",
        result_count=len(results_dto),
        latency_ms=latency_ms,
        degraded=degraded,
        aha_moment=aha,
        suggest_live=suggest_live_flag,
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
        sources = [MatchSourceDTO(**s) for s in row.match_sources or []]
        if row.stub_id:
            stub = await db.get(PublicBusinessStub, row.stub_id)
            if not stub:
                continue
            org = await db.get(Organization, stub.org_id)
            org_name = org.name if org else ""
            pub = type(
                "Pub",
                (),
                {
                    "stub_id": stub.id,
                    "org_id": stub.org_id,
                    "org_name": org_name,
                    "display_name": stub.display_name,
                    "company_name": stub.company_name,
                    "title": stub.title,
                    "product_keywords": list(stub.product_keywords or []),
                    "external_card_url": stub.external_card_url,
                },
            )()
            item = type(
                "R",
                (),
                {"match_reason": row.match_reason, "match_sources": row.match_sources or []},
            )()
            items.append(
                _public_result_dto(row.rank, item, pub, row.match_score, sources)
            )
            continue

        if not row.contact_id:
            continue
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
                match_sources=sources,
                source_pool=row.source_pool or "private_rolodex",
                contact_preview=_preview_from_candidate(cand),
                live_products=row.live_products if row.live_products else None,
            )
        )

    return SearchQueryResponse(
        query_id=query_row.id,
        status=query_row.status,
        result_count=query_row.result_count,
        latency_ms=query_row.latency_ms,
        degraded=query_row.degraded,
        suggest_live=query_row.suggest_live,
        results=items,
    )
