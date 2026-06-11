"""M3.5 person enrichment orchestration (Pro).

Flow (manual / from_search):
  quota → resolve candidates → (disambiguation) → match gate → LLM summarize
  → confidence gate → write person_enrichments + contact fields → re-index

URL-auto (Pro + auto_on_url) runs the same pipeline in the background with no quota.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipelines.person_enrich import (
    PersonCandidate,
    build_card_inference_candidate,
    fetch_by_url,
    person_search_is_mock,
    search_people,
    summarize_person_scope,
)
from app.core.config import get_settings
from app.core.entitlements import (
    consume_person_linkedin_quota,
    is_person_enrich_allowed,
    person_linkedin_remaining,
    reset_person_linkedin_quota_if_needed,
)
from app.models.contact import Contact
from app.models.person_enrich import PersonEnrichment, PersonEnrichJob
from app.models.user import User, UserEntitlement

settings = get_settings()

DUPLICATE_WINDOW_HOURS = 24
# Manual clicks bypass the 24h idempotent skip; only block rapid duplicate submits.
MANUAL_DUPLICATE_WINDOW_SECONDS = 15


async def _load_contact(db: AsyncSession, contact_id: uuid.UUID, user_id: uuid.UUID) -> Contact | None:
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.user_id == user_id,
            Contact.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def _latest_active(db: AsyncSession, contact_id: uuid.UUID) -> PersonEnrichment | None:
    result = await db.execute(
        select(PersonEnrichment)
        .where(PersonEnrichment.contact_id == contact_id, PersonEnrichment.status == "active")
        .order_by(PersonEnrichment.enrich_version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_job(db: AsyncSession, contact_id: uuid.UUID) -> PersonEnrichJob | None:
    result = await db.execute(
        select(PersonEnrichJob)
        .where(PersonEnrichJob.contact_id == contact_id)
        .order_by(PersonEnrichJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _candidate_payload(c: PersonCandidate, index: int) -> dict:
    return {
        "index": index,
        "linkedin_url": c.linkedin_url,
        "headline": c.headline,
        "match_score": c.match_score,
    }


async def _next_version(db: AsyncSession, contact_id: uuid.UUID) -> int:
    result = await db.execute(
        select(PersonEnrichment.enrich_version)
        .where(PersonEnrichment.contact_id == contact_id)
        .order_by(PersonEnrichment.enrich_version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    return (latest or 0) + 1


async def _supersede_active(db: AsyncSession, contact_id: uuid.UUID) -> None:
    rows = await db.execute(
        select(PersonEnrichment).where(
            PersonEnrichment.contact_id == contact_id, PersonEnrichment.status == "active"
        )
    )
    for row in rows.scalars().all():
        row.status = "superseded"


async def _write_result(
    db: AsyncSession,
    *,
    contact: Contact,
    candidate: PersonCandidate,
    scope: str,
    confidence: float,
    match_score: float,
    trigger: str,
    model: str,
    prompt_version: str,
    entitlement: UserEntitlement | None = None,
) -> PersonEnrichment:
    await _supersede_active(db, contact.id)
    version = await _next_version(db, contact.id)
    enrichment = PersonEnrichment(
        contact_id=contact.id,
        user_id=contact.user_id,
        enrich_version=version,
        trigger_type=trigger,
        source_type=candidate.source_type,
        linkedin_url=candidate.linkedin_url or contact.linkedin_url,
        profile_headline=candidate.headline,
        profile_summary=candidate.summary,
        person_scope=scope,
        confidence=confidence,
        match_score=match_score,
        match_inputs=candidate.match_inputs,
        model=model,
        prompt_version=prompt_version,
        status="active",
    )
    db.add(enrichment)
    contact.person_scope = scope
    contact.person_scope_confidence = confidence
    contact.person_enrich_status = "completed"
    contact.person_enriched_at = datetime.now(UTC)
    if candidate.linkedin_url and not contact.linkedin_url:
        contact.linkedin_url = candidate.linkedin_url
    if entitlement and _uses_linkedin_quota(
        candidate,
        trigger=trigger,
        has_linkedin_url=bool(contact.linkedin_url),
    ):
        await consume_person_linkedin_quota(db, entitlement)
    return enrichment


async def _finish_job(
    job: PersonEnrichJob,
    *,
    status: str,
    started: datetime,
    error_code: str | None = None,
    candidates: list[dict] | None = None,
) -> None:
    job.status = status
    job.error_code = error_code
    job.candidates = candidates
    job.completed_at = datetime.now(UTC)
    job.latency_ms = int((job.completed_at - started).total_seconds() * 1000)


def _uses_linkedin_quota(
    candidate: PersonCandidate,
    *,
    trigger: str,
    has_linkedin_url: bool,
) -> bool:
    if trigger == "url_auto":
        return False
    if candidate.source_type in ("linkedin_url", "people_api"):
        return True
    # 手動「從 LinkedIn 更新」走公開網路摘要時仍計入本月 LinkedIn 更新次數。
    if trigger == "manual" and has_linkedin_url and candidate.source_type == "web_search":
        return True
    return False


def _confidence_gate(candidate: PersonCandidate) -> float:
    if candidate.source_type == "card_inference":
        return settings.person_confidence_gate_card
    if candidate.source_type == "web_search":
        return settings.person_confidence_gate_web
    return settings.person_confidence_gate


def person_data_source(enrichment: PersonEnrichment | None) -> str | None:
    if not enrichment or not enrichment.person_scope:
        return None
    st = enrichment.source_type
    if st == "linkedin_url":
        ds = "linkedin_profile"
    elif st == "people_api":
        # Legacy mock rows stored as people_api without a LinkedIn URL.
        ds = "card_inference" if not enrichment.linkedin_url else "linkedin_search"
    elif st == "card_inference":
        ds = "card_inference"
    elif st == "user_manual":
        ds = "user_manual"
    elif st == "web_search":
        ds = "linkedin_url_public"
    else:
        ds = st
    # 防冒充紅線（DDR-83/紅旗 2）：未接官方 LinkedIn API 時，
    # 任何「✦ LinkedIn」級來源都降級為名片推估，UI 不得冒充 LinkedIn 真資料。
    if ds in ("linkedin_profile", "linkedin_search") and person_search_is_mock():
        return "card_inference"
    return ds


def person_provenance_label(enrichment: PersonEnrichment | None) -> str | None:
    if not enrichment or not enrichment.person_scope:
        return None
    conf = int((enrichment.confidence or 0) * 100)
    ds = person_data_source(enrichment)
    if ds == "linkedin_profile":
        return f"✦ LinkedIn 個人頁 · AI 整理 · {conf}%"
    if ds == "linkedin_search":
        return f"✦ LinkedIn 搜尋 · AI 整理 · {conf}%"
    if ds == "card_inference":
        hint = ""
        if person_search_is_mock():
            hint = "（開發環境未接 LinkedIn API）"
        return f"○ 名片推估（未找到 LinkedIn）· AI 整理 · {conf}%{hint}"
    if ds == "user_manual":
        return "✎ 使用者筆記"
    if ds == "linkedin_url_public":
        return f"○ 依連結公開摘要 · AI 整理 · {conf}%"
    return f"○ AI 整理 · {conf}%"


async def write_manual_person_scope(db: AsyncSession, contact: Contact, scope: str) -> None:
    """Persist user-edited person scope (does not consume LinkedIn quota)."""
    text = scope.strip()
    if not text:
        return
    if not text.startswith("可能負責"):
        text = f"可能負責{text.lstrip('可能负责').lstrip('可能負責')}"

    await _supersede_active(db, contact.id)
    version = await _next_version(db, contact.id)
    enrichment = PersonEnrichment(
        contact_id=contact.id,
        user_id=contact.user_id,
        enrich_version=version,
        trigger_type="manual",
        source_type="user_manual",
        person_scope=text,
        confidence=1.0,
        match_score=1.0,
        match_inputs={"source": "user_manual"},
        model="user",
        prompt_version="manual",
        status="active",
    )
    db.add(enrichment)
    contact.person_scope = text
    contact.person_scope_confidence = 1.0
    contact.person_enrich_status = "completed"
    contact.person_enriched_at = datetime.now(UTC)


async def clear_person_scope(db: AsyncSession, contact: Contact) -> None:
    await _supersede_active(db, contact.id)
    contact.person_scope = None
    contact.person_scope_confidence = None
    contact.person_enrich_status = "never"
    contact.person_enriched_at = None


async def _finish_insufficient(
    db: AsyncSession,
    *,
    contact: Contact,
    job: PersonEnrichJob,
    started: datetime,
    confidence: float,
    gate: float,
    data_source: str,
) -> dict:
    await _finish_job(job, status="completed", started=started, error_code="LOW_CONFIDENCE")
    contact.person_scope = None
    contact.person_scope_confidence = None
    contact.person_enrich_status = "insufficient"
    await db.commit()
    pct = int(confidence * 100)
    gate_pct = int(gate * 100)
    return {
        "status": "insufficient",
        "confidence": confidence,
        "data_source": data_source,
        "message": f"AI 整理信心 {pct}% 低於門檻 {gate_pct}%，未寫入此區塊。",
    }


async def _finish_linkedin_fetch_failed(
    db: AsyncSession,
    *,
    contact: Contact,
    job: PersonEnrichJob,
    started: datetime,
) -> dict:
    """User provided LinkedIn URL but profile content could not be retrieved."""
    await _finish_job(job, status="completed", started=started, error_code="LINKEDIN_FETCH_FAILED")
    contact.person_scope = None
    contact.person_scope_confidence = None
    contact.person_enrich_status = "insufficient"
    await db.commit()
    hint = ""
    if person_search_is_mock():
        hint = "（公開網路也找不到可用摘要，可改為自行輸入）"
    return {
        "status": "insufficient",
        "data_source": "unavailable",
        "message": (
            "無法從公開網路取得此 LinkedIn 連結的可用摘要，未寫入此區塊。"
            " 請確認連結是否正確，或改為自行輸入。"
            f"{hint}"
        ),
    }


async def _process_candidate(
    db: AsyncSession,
    *,
    contact: Contact,
    candidate: PersonCandidate,
    trigger: str,
    job: PersonEnrichJob,
    started: datetime,
    skip_match_gate: bool = False,
    entitlement: UserEntitlement | None = None,
) -> dict:
    """Apply match + confidence gates, summarize, write. Returns status dict."""
    if not skip_match_gate and candidate.match_score < settings.person_match_gate:
        # surface as needs_confirmation (R-35.2: do not write below gate)
        await _finish_job(
            job,
            status="needs_confirmation",
            started=started,
            candidates=[_candidate_payload(candidate, 0)],
        )
        contact.person_enrich_status = "pending"
        await db.commit()
        return {"status": "needs_confirmation", "candidates": [_candidate_payload(candidate, 0)]}

    output, model, prompt_version = await summarize_person_scope(
        candidate,
        name=contact.display_name or "",
        title=contact.title,
        company_name=contact.company_name,
    )

    gate = _confidence_gate(candidate)
    if output.confidence < gate:
        ds_by_source = {
            "card_inference": "card_inference",
            "web_search": "linkedin_url_public",
        }
        ds = ds_by_source.get(candidate.source_type, "linkedin_search")
        return await _finish_insufficient(
            db,
            contact=contact,
            job=job,
            started=started,
            confidence=output.confidence,
            gate=gate,
            data_source=ds,
        )

    await _write_result(
        db,
        contact=contact,
        candidate=candidate,
        scope=output.scope,
        confidence=output.confidence,
        match_score=candidate.match_score,
        trigger=trigger,
        model=model,
        prompt_version=prompt_version,
        entitlement=entitlement,
    )
    await _finish_job(job, status="completed", started=started)
    await db.commit()

    from app.workers.tasks.contact_index import enqueue_contact_index

    enqueue_contact_index(contact.id)
    enrichment = await _latest_active(db, contact.id)
    return {
        "status": "completed",
        "person_scope": output.scope,
        "confidence": output.confidence,
        "match_score": candidate.match_score,
        "data_source": person_data_source(enrichment),
        "provenance_label": person_provenance_label(enrichment),
    }


async def start_person_enrich(
    db: AsyncSession,
    user: User,
    contact_id: uuid.UUID,
    *,
    confirm_candidate_index: int | None = None,
    trigger: str = "manual",
) -> dict:
    """Manual / from_search entry. Consumes quota (unless confirming a prior candidate)."""
    if not is_person_enrich_allowed(user.entitlement):
        raise HTTPException(status_code=403, detail="PERSON_ENRICH_NOT_ALLOWED")

    contact = await _load_contact(db, contact_id, user.id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    running = await _latest_job(db, contact_id)
    if running and running.status == "running":
        raise HTTPException(status_code=409, detail="PERSON_ENRICH_IN_PROGRESS")

    if trigger == "manual" and contact.linkedin_url:
        await reset_person_linkedin_quota_if_needed(db, user.entitlement)
        if person_linkedin_remaining(user.entitlement) == 0:
            raise HTTPException(status_code=429, detail="PERSON_LINKEDIN_QUOTA_EXCEEDED")

    # Confirm path: reuse prior candidates, no new quota charge.
    if confirm_candidate_index is not None:
        prior = running
        if not prior or not prior.candidates:
            raise HTTPException(status_code=409, detail="NO_PENDING_CANDIDATES")
        picked = next(
            (c for c in prior.candidates if c.get("index") == confirm_candidate_index), None
        )
        if picked is None:
            raise HTTPException(status_code=400, detail="INVALID_CANDIDATE_INDEX")
        candidate = PersonCandidate(
            linkedin_url=picked.get("linkedin_url"),
            headline=picked.get("headline"),
            summary=picked.get("headline"),
            match_score=max(float(picked.get("match_score", 0.0)), settings.person_match_gate),
            match_inputs={"confirmed": True},
            source_type="people_api",
        )
        job = PersonEnrichJob(
            contact_id=contact.id,
            user_id=user.id,
            trigger_type=trigger,
            status="running",
            started_at=datetime.now(UTC),
            idempotency_key=f"person:{contact.id}:confirm:{uuid.uuid4().hex[:12]}",
        )
        db.add(job)
        await db.flush()
        return await _process_candidate(
            db,
            contact=contact,
            candidate=candidate,
            trigger=trigger,
            job=job,
            started=job.started_at,
            entitlement=user.entitlement,
        )

    # R-35.8: idempotent — recent active result returned without quota charge.
    # Manual refresh always re-runs (user explicitly requested); only debounce rapid double-clicks.
    active = await _latest_active(db, contact_id)
    if active and active.created_at:
        if trigger == "manual":
            recent_manual = (
                active.trigger_type == "manual"
                and active.created_at > datetime.now(UTC) - timedelta(seconds=MANUAL_DUPLICATE_WINDOW_SECONDS)
            )
            if recent_manual:
                return {
                    "status": "completed",
                    "person_scope": active.person_scope,
                    "confidence": active.confidence,
                    "match_score": active.match_score,
                    "data_source": person_data_source(active),
                    "provenance_label": person_provenance_label(active),
                    "quota_remaining": person_linkedin_remaining(user.entitlement),
                    "idempotent": True,
                }
        elif active.created_at > datetime.now(UTC) - timedelta(hours=DUPLICATE_WINDOW_HOURS):
            return {
                "status": "completed",
                "person_scope": active.person_scope,
                "confidence": active.confidence,
                "match_score": active.match_score,
                "data_source": person_data_source(active),
                "provenance_label": person_provenance_label(active),
                "quota_remaining": person_linkedin_remaining(user.entitlement),
                "idempotent": True,
            }

    job = PersonEnrichJob(
        contact_id=contact.id,
        user_id=user.id,
        trigger_type=trigger,
        status="running",
        started_at=datetime.now(UTC),
        idempotency_key=f"person:{contact.id}:{trigger}:{uuid.uuid4().hex[:12]}",
    )
    db.add(job)
    contact.person_enrich_status = "pending"
    await db.flush()
    started = job.started_at

    if contact.linkedin_url:
        candidate = await fetch_by_url(
            contact.linkedin_url,
            name=contact.display_name,
            title=contact.title,
            company_name=contact.company_name,
        )
        if candidate is None:
            return await _finish_linkedin_fetch_failed(
                db, contact=contact, job=job, started=started
            )
        result = await _process_candidate(
            db,
            contact=contact,
            candidate=candidate,
            trigger=trigger,
            job=job,
            started=started,
            entitlement=user.entitlement,
        )
    else:
        candidates = await search_people(
            name=contact.display_name or "",
            company_name=contact.company_name,
            title=contact.title,
        )
        if not candidates:
            candidate = build_card_inference_candidate(
                name=contact.display_name or "",
                company_name=contact.company_name,
                title=contact.title,
            )
            result = await _process_candidate(
                db,
                contact=contact,
                candidate=candidate,
                trigger=trigger,
                job=job,
                started=started,
                skip_match_gate=True,
                entitlement=user.entitlement,
            )
        elif len(candidates) > 1:
            payload = [_candidate_payload(c, i) for i, c in enumerate(candidates)]
            await _finish_job(job, status="needs_confirmation", started=started, candidates=payload)
            contact.person_enrich_status = "pending"
            await db.commit()
            result = {"status": "needs_confirmation", "candidates": payload}
        else:
            result = await _process_candidate(
                db,
                contact=contact,
                candidate=candidates[0],
                trigger=trigger,
                job=job,
                started=started,
                entitlement=user.entitlement,
            )

    result["quota_remaining"] = person_linkedin_remaining(user.entitlement)
    return result


async def reject_person_enrich(db: AsyncSession, user: User, contact_id: uuid.UUID) -> dict:
    """User says 'not this person' — clear person_scope, mark rejected, re-index."""
    contact = await _load_contact(db, contact_id, user.id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await _supersede_active(db, contact_id)
    rejected = PersonEnrichment(
        contact_id=contact.id,
        user_id=user.id,
        enrich_version=await _next_version(db, contact.id),
        trigger_type="manual",
        source_type="people_api",
        confidence=0.0,
        match_score=0.0,
        status="rejected",
    )
    db.add(rejected)
    contact.person_scope = None
    contact.person_scope_confidence = None
    contact.person_enrich_status = "rejected"
    await db.commit()

    from app.workers.tasks.contact_index import enqueue_contact_index

    enqueue_contact_index(contact.id)
    return {"status": "rejected"}


async def get_status(db: AsyncSession, contact_id: uuid.UUID, user_id: uuid.UUID) -> dict:
    contact = await _load_contact(db, contact_id, user_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    job = await _latest_job(db, contact_id)
    active = await _latest_active(db, contact_id)

    if active:
        return {
            "status": "completed",
            "person_scope": active.person_scope,
            "confidence": active.confidence,
            "match_score": active.match_score,
            "source_type": active.source_type,
            "updated_at": active.created_at.isoformat() if active.created_at else None,
            "data_source": person_data_source(active),
            "provenance_label": person_provenance_label(active),
        }
    if job and job.status == "needs_confirmation":
        return {"status": "needs_confirmation", "candidates": job.candidates or []}
    if job:
        return {"status": job.status, "error_code": job.error_code}
    return {"status": contact.person_enrich_status or "never"}


async def run_person_enrich_url_auto(payload: dict) -> None:
    """Background URL-auto runner (Pro + auto_on_url). No quota charge."""
    from sqlalchemy.orm import selectinload

    from app.core.db import async_session_factory

    contact_id = uuid.UUID(payload["contact_id"])
    user_id = uuid.UUID(payload["user_id"])

    async with async_session_factory() as db:
        user_result = await db.execute(
            select(User).where(User.id == user_id).options(selectinload(User.entitlement))
        )
        user = user_result.scalar_one_or_none()
        if not user or not is_person_enrich_allowed(user.entitlement):
            return
        await reset_person_linkedin_quota_if_needed(db, user.entitlement)

        contact = await _load_contact(db, contact_id, user_id)
        if not contact or not contact.linkedin_url:
            return

        job = PersonEnrichJob(
            contact_id=contact.id,
            user_id=user_id,
            trigger_type="url_auto",
            status="running",
            started_at=datetime.now(UTC),
            idempotency_key=f"person:{contact.id}:url_auto:{uuid.uuid4().hex[:12]}",
        )
        db.add(job)
        contact.person_enrich_status = "pending"
        await db.flush()

        candidate = await fetch_by_url(
            contact.linkedin_url,
            name=contact.display_name,
            title=contact.title,
            company_name=contact.company_name,
        )
        if candidate is None:
            await _finish_linkedin_fetch_failed(
                db, contact=contact, job=job, started=job.started_at
            )
            return
        await _process_candidate(
            db,
            contact=contact,
            candidate=candidate,
            trigger="url_auto",
            job=job,
            started=job.started_at,
        )
