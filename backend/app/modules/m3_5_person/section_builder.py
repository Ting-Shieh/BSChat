"""Build the M3.5 person-enrich section for contact detail."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlements import is_person_enrich_allowed, person_linkedin_remaining
from app.models.contact import Contact
from app.models.person_enrich import PersonEnrichJob, PersonEnrichment
from app.models.user import UserEntitlement
from app.modules.m3_5_person.service import person_data_source, person_provenance_label
from app.schemas.contact import PersonEnrichSection


async def build_person_enrich_section(
    db: AsyncSession,
    *,
    contact: Contact,
    entitlement: UserEntitlement | None,
) -> PersonEnrichSection:
    is_pro = bool(entitlement and is_person_enrich_allowed(entitlement))
    has_url = bool(contact.linkedin_url)

    if not is_pro:
        # Free: locked — show upgrade CTA in UI.
        return PersonEnrichSection(status="locked", is_pro=False, has_linkedin_url=has_url)

    remaining = person_linkedin_remaining(entitlement) if entitlement else 0
    quota_remaining = None if remaining < 0 else remaining
    can_enrich = remaining != 0  # -1 unlimited or > 0

    if contact.person_scope and contact.person_enrich_status == "completed":
        active = await _latest_active(db, contact.id)
        return PersonEnrichSection(
            status="completed",
            is_pro=True,
            person_scope=contact.person_scope,
            confidence=contact.person_scope_confidence,
            data_source=person_data_source(active),
            provenance_label=person_provenance_label(active),
            updated_at=contact.person_enriched_at.isoformat() if contact.person_enriched_at else None,
            quota_remaining=quota_remaining,
            can_enrich=can_enrich,
            has_linkedin_url=has_url,
            has_m3_fallback=bool(contact.responsibility_scope),
        )

    stale_completed = contact.person_enrich_status == "completed" and not contact.person_scope
    if contact.person_enrich_status == "insufficient" or stale_completed:
        job = await _latest_job(db, contact.id)
        msg = (
            "上次補充信心不足，未寫入此區塊。"
            if stale_completed
            else "AI 整理信心不足，未寫入此區塊。"
        )
        if job and job.error_code == "LOW_CONFIDENCE":
            msg = (
                "AI 整理信心低於門檻，未寫入此區塊。"
                " 可編輯聯絡人補上 LinkedIn 後再試，或參考上方「系統參考（名片推估）」。"
            )
        elif job and job.error_code == "LINKEDIN_FETCH_FAILED":
            msg = (
                "無法從公開網路取得此 LinkedIn 連結的可用摘要，未寫入此區塊。"
                " 請確認連結是否正確，或改為自行輸入。"
            )
        return PersonEnrichSection(
            status="insufficient",
            is_pro=True,
            message=msg,
            has_m3_fallback=bool(contact.responsibility_scope),
            quota_remaining=quota_remaining,
            can_enrich=can_enrich,
            has_linkedin_url=has_url,
        )

    job = await _latest_job(db, contact.id)
    if job and job.status == "needs_confirmation":
        return PersonEnrichSection(
            status="needs_confirmation",
            is_pro=True,
            candidates=job.candidates or [],
            quota_remaining=quota_remaining,
            can_enrich=can_enrich,
            has_linkedin_url=has_url,
        )
    if contact.person_enrich_status == "rejected":
        return PersonEnrichSection(
            status="rejected", is_pro=True, quota_remaining=quota_remaining,
            can_enrich=can_enrich, has_linkedin_url=has_url,
        )
    if contact.person_enrich_status == "pending":
        return PersonEnrichSection(
            status="pending", is_pro=True, quota_remaining=quota_remaining,
            can_enrich=False, has_linkedin_url=has_url,
        )

    return PersonEnrichSection(
        status="never",
        is_pro=True,
        quota_remaining=quota_remaining,
        can_enrich=can_enrich,
        has_linkedin_url=has_url,
        has_m3_fallback=bool(contact.responsibility_scope),
    )


async def _latest_active(db: AsyncSession, contact_id) -> PersonEnrichment | None:
    result = await db.execute(
        select(PersonEnrichment)
        .where(PersonEnrichment.contact_id == contact_id, PersonEnrichment.status == "active")
        .order_by(PersonEnrichment.enrich_version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_job(db: AsyncSession, contact_id) -> PersonEnrichJob | None:
    result = await db.execute(
        select(PersonEnrichJob)
        .where(PersonEnrichJob.contact_id == contact_id)
        .order_by(PersonEnrichJob.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
