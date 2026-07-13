import time
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.entitlements import reset_live_augment_quota_if_needed, reset_search_cache_quota_if_needed
from app.core.media_urls import public_media_url
from app.ai.pipelines.search_intent import INTENT_PROMPT_VERSION, parse_intent
from app.ai.pipelines.search_rerank import PROMPT_VERSION as RERANK_PROMPT_VERSION, rerank_contacts
from app.models.contact import Contact
from app.models.organization import Organization
from app.models.public_business_stub import PublicBusinessStub
from app.models.search import SearchQuery, SearchResult
from app.models.user import User, UserEntitlement
from app.modules.m5_search.constraints import filter_rerank_results
from app.modules.m5_search.precision import normalize_precision, precision_empty_hint
from app.modules.m5_search.retrieval import (
    CandidateDoc,
    PublicCandidateDoc,
    candidate_to_dict,
    count_indexed,
    count_public_published,
    public_candidate_to_dict,
    public_to_candidate_doc,
    retrieve_candidates,
    retrieve_public_candidates,
)
from app.modules.m5_search.hybrid import PoolRetrievalDebug, build_semantic_query
from app.modules.m5_search.public_search import ALLOWED_SEARCH_SCOPES, can_use_network_scope
from app.modules.m5_search.sample_queries import pick_sample_queries
from app.modules.m5_search.live_augment import should_suggest_live
from app.modules.m5_search.validate import apply_confirmed_boost, validate_rerank_item
from app.schemas.search import (
    BriefingDTO,
    ContactPreviewDTO,
    CreateSearchQueryRequest,
    MatchSourceDTO,
    PoolRetrievalDebugDTO,
    RetrievalCandidateDebugDTO,
    SearchDebugDTO,
    SearchEmptyStateDTO,
    SearchQueryResponse,
    SearchQuotasDTO,
    SearchResultItemDTO,
    SearchStatusResponse,
    StubPreviewDTO,
)

DORMANT_THRESHOLD_MONTHS = 6


def _dormant_months(created_at: datetime | None) -> int | None:
    """Proxy for 'time since last touched': months since the card was captured.

    v1 has no explicit last_contacted_at; capture time is the honest stand-in
    (see PRD v3 商機簡報 · dormant hook).
    """
    if created_at is None:
        return None
    now = datetime.now(UTC)
    ref = created_at if created_at.tzinfo else created_at.replace(tzinfo=UTC)
    days = (now - ref).days
    if days < 0:
        return None
    return days // 30


def _build_briefing_headline(*, scanned: int, match_count: int, dormant_count: int) -> str:
    if match_count == 0:
        return f"翻過你名片庫的 {scanned} 張，這次沒有對得上的。"
    parts = [f"翻過你名片庫的 {scanned} 張，有 {match_count} 位跟這個需求對得上。"]
    if dormant_count > 0:
        parts.append(f"其中 {dormant_count} 位你已超過半年沒動作，差點被埋在抽屜裡。")
    return "".join(parts)


def _search_debug_enabled() -> bool:
    settings = get_settings()
    return settings.search_debug_enabled or settings.debug


def _pool_debug_dto(pool: PoolRetrievalDebug | None) -> PoolRetrievalDebugDTO | None:
    if pool is None:
        return None
    return PoolRetrievalDebugDTO(
        pool=pool.pool,
        lexical_query=pool.lexical_query,
        semantic_query=pool.semantic_query,
        ts_hits=pool.ts_hits,
        trgm_extra_hits=pool.trgm_extra_hits,
        vector_hits=pool.vector_hits,
        widened=pool.widened,
        top_candidates=[
            RetrievalCandidateDebugDTO(
                id=c.id,
                label=c.label,
                retrieval_score=c.retrieval_score,
            )
            for c in pool.top_candidates
        ],
    )


def _build_search_debug(
    *,
    scope: str,
    precision: str,
    intent,
    query_text: str,
    private_debug: PoolRetrievalDebug | None,
    public_debug: PoolRetrievalDebug | None,
    rerank_input_count: int,
    result_count: int,
    degraded: bool,
    latency_ms: int | None,
) -> SearchDebugDTO | None:
    if not _search_debug_enabled():
        return None
    return SearchDebugDTO(
        search_scope=scope,
        search_precision=precision,
        intent_prompt_version=INTENT_PROMPT_VERSION,
        rerank_prompt_version=RERANK_PROMPT_VERSION,
        semantic_query=build_semantic_query(intent, query_text),
        parsed_intent=intent.model_dump(),
        private=_pool_debug_dto(private_debug),
        public=_pool_debug_dto(public_debug),
        rerank_input_count=rerank_input_count,
        result_count=result_count,
        degraded=degraded,
        latency_ms=latency_ms,
    )


def _debug_from_stored(stored: dict | None) -> SearchDebugDTO | None:
    if not stored or not _search_debug_enabled():
        return None
    raw = stored.get("search_debug")
    if not raw:
        return None
    return SearchDebugDTO.model_validate(raw)


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
    ent = user.entitlement

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

    private_had_candidates = False
    public_had_candidates = False

    private_candidates: list[CandidateDoc] = []
    public_candidates: list[PublicCandidateDoc] = []
    private_debug: PoolRetrievalDebug | None = None
    public_debug: PoolRetrievalDebug | None = None
    if include_private and indexed > 0:
        private_candidates, private_debug = await retrieve_candidates(
            db, user_id=user.id, query_text=body.query_text, intent=intent
        )
        private_had_candidates = bool(private_candidates)
    if include_public and public_pool > 0:
        public_candidates, public_debug = await retrieve_public_candidates(
            db, query_text=body.query_text, intent=intent
        )
        public_had_candidates = bool(public_candidates)

    private_map = {str(c.contact_id): c for c in private_candidates}
    public_map = {str(c.stub_id): c for c in public_candidates}
    cand_map = {
        **private_map,
        **{sid: public_to_candidate_doc(pc) for sid, pc in public_map.items()},
    }

    merged_for_rerank: list[tuple[float, dict]] = []
    for c in private_candidates:
        merged_for_rerank.append((float(c.retrieval_score), candidate_to_dict(c)))
    for c in public_candidates:
        merged_for_rerank.append((float(c.retrieval_score), public_candidate_to_dict(c)))
    merged_for_rerank.sort(key=lambda x: x[0], reverse=True)
    rerank_input = [d for _, d in merged_for_rerank[: get_settings().search_rerank_input_max]]

    precision = normalize_precision(ent.search_precision)
    private_validated: list[tuple[object, CandidateDoc]] = []
    public_validated: list[tuple[object, PublicCandidateDoc]] = []

    if rerank_input:
        rerank_resp, degraded = await rerank_contacts(
            body.query_text,
            rerank_input,
            intent,
            search_precision=precision,
        )
        filtered = filter_rerank_results(rerank_resp.results, cand_map, intent)
        for item in filtered:
            cand = cand_map.get(item.contact_id)
            if not cand or not validate_rerank_item(item, cand):
                continue
            if item.contact_id in private_map:
                private_validated.append((item, private_map[item.contact_id]))
            elif item.contact_id in public_map:
                public_validated.append((item, public_map[item.contact_id]))

    combined: list[tuple[str, float, object, object]] = []
    for item, cand in private_validated:
        score = apply_confirmed_boost(float(item.match_score), cand.review_status)
        combined.append(("private", score, item, cand))
    for item, pub in public_validated:
        combined.append(("public", float(item.match_score), item, pub))
    combined.sort(key=lambda x: x[1], reverse=True)
    combined = combined[:10]

    latency_ms = int((time.perf_counter() - started) * 1000)
    debug_dto = _build_search_debug(
        scope=scope,
        precision=precision,
        intent=intent,
        query_text=body.query_text,
        private_debug=private_debug,
        public_debug=public_debug,
        rerank_input_count=len(rerank_input),
        result_count=0,
        degraded=degraded,
        latency_ms=latency_ms,
    )

    if not combined:
        reason = "NO_MATCH"
        if scope == "network":
            reason = "NO_MATCH_PUBLIC"
        elif indexed < 3 and not private_had_candidates and not public_had_candidates:
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
        hint = precision_empty_hint(precision) if reason in ("NO_MATCH", "NO_MATCH_PUBLIC") else None
        stored["search_precision"] = precision
        if hint:
            stored["precision_hint"] = hint
        if debug_dto:
            stored["search_debug"] = debug_dto.model_dump()
        query_row.parsed_intent = stored
        await db.commit()
        return SearchQueryResponse(
            query_id=query_row.id,
            status="EMPTY",
            latency_ms=latency_ms,
            degraded=degraded,
            debug=debug_dto,
            empty_state=SearchEmptyStateDTO(
                reason=reason,
                suggestions=suggestions,
                sample_queries=await pick_sample_queries(db, user),
                cta={"action": "capture", "label": "去收錄名片"} if indexed < 3 and scope != "network" else None,
                search_precision=precision,
                precision_hint=hint,
            ),
        )

    had_prior = await _had_successful_search(db, user.id)
    results_dto: list[SearchResultItemDTO] = []
    private_ids: list[uuid.UUID] = []

    private_combined_ids = [entity.contact_id for pool, _, _, entity in combined if pool == "private"]
    dormant_map: dict[uuid.UUID, int | None] = {}
    if private_combined_ids:
        rows = await db.execute(
            select(Contact.id, Contact.created_at).where(Contact.id.in_(private_combined_ids))
        )
        for cid, created in rows.all():
            dormant_map[cid] = _dormant_months(created)

    for rank, (pool, score, item, entity) in enumerate(combined, start=1):
        sources = [
            MatchSourceDTO(field=s.field, value=s.value, confidence=s.confidence)
            for s in (getattr(item, "match_sources", None) or [])
        ]
        if pool == "private":
            cand = entity
            private_ids.append(cand.contact_id)
            opening_line = getattr(item, "opening_line", None)
            collaboration_note = getattr(item, "collaboration_note", None)
            dormant = dormant_map.get(cand.contact_id)
            db.add(
                SearchResult(
                    query_id=query_row.id,
                    contact_id=cand.contact_id,
                    rank=rank,
                    match_score=score,
                    match_reason=item.match_reason,
                    match_sources=[s.model_dump() for s in sources],
                    source_pool="private_rolodex",
                    opening_line=opening_line,
                    collaboration_note=collaboration_note,
                    dormant_months=dormant,
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
                    opening_line=opening_line,
                    collaboration_note=collaboration_note,
                    dormant_months=dormant,
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

    briefing: BriefingDTO | None = None
    if private_combined_ids:
        dormant_count = sum(
            1
            for cid in private_combined_ids
            if (dormant_map.get(cid) or 0) >= DORMANT_THRESHOLD_MONTHS
        )
        briefing = BriefingDTO(
            headline=_build_briefing_headline(
                scanned=indexed, match_count=len(private_ids), dormant_count=dormant_count
            ),
            scanned_count=indexed,
            match_count=len(private_ids),
            dormant_count=dormant_count,
        )

    stored = dict(query_row.parsed_intent or {})
    if debug_dto:
        debug_dto = debug_dto.model_copy(update={"result_count": len(results_dto)})
        stored["search_debug"] = debug_dto.model_dump()
    if briefing:
        stored["briefing"] = briefing.model_dump()
    query_row.parsed_intent = stored
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
        briefing=briefing,
        debug=debug_dto,
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
            degraded=query_row.degraded,
            debug=_debug_from_stored(stored),
            empty_state=SearchEmptyStateDTO(
                reason=reason,
                suggestions=suggestions,
                sample_queries=await pick_sample_queries(db, user),
                search_precision=stored.get("search_precision"),
                precision_hint=stored.get("precision_hint"),
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
                opening_line=row.opening_line,
                collaboration_note=row.collaboration_note,
                dormant_months=row.dormant_months,
            )
        )

    stored_briefing = (query_row.parsed_intent or {}).get("briefing")
    briefing = BriefingDTO.model_validate(stored_briefing) if stored_briefing else None

    return SearchQueryResponse(
        query_id=query_row.id,
        status=query_row.status,
        result_count=query_row.result_count,
        latency_ms=query_row.latency_ms,
        degraded=query_row.degraded,
        suggest_live=query_row.suggest_live,
        results=items,
        briefing=briefing,
        debug=_debug_from_stored(query_row.parsed_intent),
    )
