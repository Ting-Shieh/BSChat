"""Pro Stage 1 E2E: settings API + M5 Layer3 live augment."""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import async_session_factory
from app.main import app
from app.models.company import Company
from app.models.contact import Contact
from app.modules.m3_contacts.index_builder import index_contact


async def _login(
    client: AsyncClient,
    *,
    email: str | None = None,
    plan_tier: str = "free",
) -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={
            "email": email or f"pro-stage1-{uuid.uuid4()}@example.com",
            "display_name": "Stage1 Test",
            "plan_tier": plan_tier,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _sync_index_enqueue(monkeypatch):
    async def _index_now(contact_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await index_contact(db, contact_id)
            await db.commit()

    def enqueue(contact_id: uuid.UUID) -> None:
        asyncio.get_running_loop().create_task(_index_now(contact_id))

    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_index", enqueue)
    monkeypatch.setattr("app.workers.tasks.contact_index.enqueue_contact_index", enqueue)


def _noop_company_enrich(monkeypatch):
    monkeypatch.setattr("app.modules.m3_contacts.upsert.dispatch_company_enrich", lambda *a, **k: None)
    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_inference", lambda *a, **k: None)


def _mock_search_llm(monkeypatch, contact_id: str):
    _mock_retrieve_contact(monkeypatch, contact_id)

    async def fake_intent(prompt: str, **kwargs):
        return """```json
{
  "products": ["嵌入式"],
  "roles": [],
  "events": [],
  "regions": [],
  "keywords": ["嵌入式", "工業"],
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}
```"""

    async def fake_rerank(prompt: str, **kwargs):
        return f"""```json
{{
  "results": [
    {{
      "contact_id": "{contact_id}",
      "match_score": 0.9,
      "match_reason": "公司產品與嵌入式相關",
      "match_sources": [{{"field": "company_name", "value": "StaleTech Inc"}}]
    }}
  ]
}}
```"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_intent)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.gemini_generate_text", fake_rerank)


def _mock_retrieve_contact(monkeypatch, contact_id: str) -> None:
    from app.modules.m5_search.retrieval import CandidateDoc

    cid = uuid.UUID(contact_id)
    doc = CandidateDoc(
        contact_id=cid,
        display_name="Live Aug Test",
        company_name="StaleTech Inc",
        title="Sales Director",
        responsibility_scope=None,
        responsibility_confidence=None,
        source_label=None,
        review_status="pending_review",
        phones=[],
        emails=[],
        image_url=None,
        company_products=[],
        products_confidence=None,
        search_text="Live Aug Test | StaleTech Inc | Sales Director",
        retrieval_score=0.6,
    )

    async def fake_retrieve(db, user_id, query_text, intent, limit=None):
        return [doc], None

    monkeypatch.setattr("app.modules.m5_search.service.retrieve_candidates", fake_retrieve)


async def _seed_contact(client: AsyncClient, headers: dict) -> tuple[str, str]:
    vcard = """BEGIN:VCARD
VERSION:3.0
FN:Live Aug Test
ORG:StaleTech Inc
TITLE:Sales Director
TEL:0911222333
EMAIL:live@test.com
END:VCARD"""
    imp = await client.post(
        "/api/v1/cards/import-qr",
        json={"payload": vcard},
        headers={**headers, "Idempotency-Key": f"stage1-{uuid.uuid4()}"},
    )
    assert imp.status_code == 201, imp.text
    card_id = imp.json()["raw_card_id"]
    review = await client.patch(
        f"/api/v1/cards/{card_id}/review",
        headers=headers,
        json={
            "name": "Live Aug Test",
            "company": "StaleTech Inc",
            "title": "Sales Director",
            "version": 1,
        },
    )
    assert review.status_code == 200, review.text
    await asyncio.sleep(0.05)
    listed = await client.get("/api/v1/contacts", headers=headers)
    contact_id = listed.json()["items"][0]["id"]
    return contact_id, card_id


async def _mark_company_stale(contact_id: str) -> None:
    async with async_session_factory() as db:
        contact = await db.get(Contact, uuid.UUID(contact_id))
        assert contact and contact.company_id
        company = await db.get(Company, contact.company_id)
        assert company
        company.enrich_status = "never"
        company.last_enriched_at = None
        await db.commit()


@pytest.mark.asyncio
async def test_pro_settings_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="pro")
        headers = {"Authorization": f"Bearer {token}"}

        before = await client.get("/api/v1/me", headers=headers)
        assert before.status_code == 200
        assert before.json()["auto_refresh"]["enabled"] is True

        patch = await client.patch(
            "/api/v1/me/settings",
            headers=headers,
            json={
                "auto_refresh_enabled": False,
                "auto_refresh_interval_days": 30,
                "person_linkedin_auto_on_url": False,
            },
        )
        assert patch.status_code == 200, patch.text
        body = patch.json()
        assert body["auto_refresh"]["enabled"] is False
        assert body["auto_refresh"]["interval_days"] == 30
        assert body["person_enrich"]["auto_on_url"] is False


@pytest.mark.asyncio
async def test_free_settings_requires_pro():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.patch(
            "/api/v1/me/settings",
            headers=headers,
            json={"auto_refresh_enabled": True},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "PRO_REQUIRED"


@pytest.mark.asyncio
async def test_live_augment_flow(monkeypatch):
    _noop_company_enrich(monkeypatch)
    _sync_index_enqueue(monkeypatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="pro")
        headers = {"Authorization": f"Bearer {token}"}

        contact_id, _ = await _seed_contact(client, headers)
        await _mark_company_stale(contact_id)

        async with async_session_factory() as db:
            await index_contact(db, uuid.UUID(contact_id))
            await db.commit()

        _mock_search_llm(monkeypatch, contact_id)

        me_before = await client.get("/api/v1/me", headers=headers)
        live_before = me_before.json()["quotas"]["live_augment_remaining_month"]

        search = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "找嵌入式相關的人", "search_scope": "private"},
        )
        assert search.status_code == 200, search.text
        data = search.json()
        assert data["status"] == "COMPLETED"
        assert data.get("suggest_live") is True
        query_id = data["query_id"]

        async def fake_query_time_extract(db, *, company_id, user_id):
            return {
                "main_products": ["嵌入式系統", "Edge AI 盒"],
                "source_urls": ["https://staletech.example.com"],
                "confidence": 0.82,
            }

        monkeypatch.setattr(
            "app.modules.m5_search.live_augment.query_time_extract",
            fake_query_time_extract,
        )

        aug = await client.post(
            f"/api/v1/search/queries/{query_id}/live-augment",
            headers=headers,
            json={},
        )
        assert aug.status_code == 200, aug.text
        aug_body = aug.json()
        assert aug_body.get("suggest_live") is False
        assert aug_body["results"]
        first = aug_body["results"][0]
        assert first["live_products"] == ["嵌入式系統", "Edge AI 盒"]
        assert "即時查詢" in first["match_reason"]

        me_after = await client.get("/api/v1/me", headers=headers)
        live_after = me_after.json()["quotas"]["live_augment_remaining_month"]
        assert live_after == live_before - 1

        async with async_session_factory() as db:
            from app.models.query_augmentation import QueryAugmentation

            rows = (
                await db.execute(
                    select(QueryAugmentation).where(QueryAugmentation.query_id == uuid.UUID(query_id))
                )
            ).scalars().all()
            assert len(rows) == 1
            assert rows[0].live_products == ["嵌入式系統", "Edge AI 盒"]

            contact = await db.get(Contact, uuid.UUID(contact_id))
            company = await db.get(Company, contact.company_id)
            # DDR-36: live augment must not write M6 cache
            assert company.enrich_status == "never"
