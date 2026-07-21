"""M5 widened recall: literal miss → pool candidates for LLM rerank (DDR-101)."""

import asyncio
import uuid

import pytest

from intent_llm_testutil import patch_intent_llm
from httpx import ASGITransport, AsyncClient

from app.core.db import async_session_factory
from app.main import app
from app.modules.m11_public_directory.index_builder import index_stub


async def _login(client: AsyncClient, *, plan_tier: str = "pro") -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={
            "email": f"semantic-{uuid.uuid4()}@example.com",
            "display_name": "Semantic Test",
            "plan_tier": plan_tier,
            "seed_org": "acme-demo",
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _sync_public_index(monkeypatch):
    async def _index_now(stub_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await index_stub(db, stub_id)
            await db.commit()

    def enqueue(stub_id: uuid.UUID) -> None:
        asyncio.get_running_loop().create_task(_index_now(stub_id))

    monkeypatch.setattr("app.modules.m11_public_directory.service.enqueue_stub_index", enqueue)
    monkeypatch.setattr("app.workers.tasks.public_directory_index.enqueue_stub_index", enqueue)


async def _ensure_published_indexed() -> uuid.UUID:
    from sqlalchemy import select

    from app.models.public_business_stub import PublicBusinessStub

    stub_id: uuid.UUID | None = None
    async with async_session_factory() as db:
        result = await db.execute(
            select(PublicBusinessStub).where(PublicBusinessStub.status == "published")
        )
        for stub in result.scalars():
            await index_stub(db, stub.id)
            if stub.display_name == "Ting Hsieh":
                stub_id = stub.id
        await db.commit()
    assert stub_id is not None
    return stub_id


@pytest.mark.asyncio
async def test_iot_query_finds_ting_hsieh_via_widened_recall(monkeypatch):
    """IoT natural language query: trgm miss → widened pool → LLM picks Ting Hsieh."""
    _sync_public_index(monkeypatch)
    ting_stub_id = await _ensure_published_indexed()

    async def fake_intent(prompt: str, **kwargs):
        return """```json
{"products": ["物聯網"], "roles": [], "events": [], "regions": [],
 "keywords": ["IOT", "物聯網"], "hard_roles": [], "hard_companies": [], "hard_products": []}
```"""

    async def fake_rerank(prompt: str, **kwargs):
        return f"""```json
{{
  "results": [
    {{
      "contact_id": "{ting_stub_id}",
      "match_score": 0.88,
      "match_reason": "ADATA AI 專案經理，產品關鍵字含 IoT，與物聯網查詢高度相關",
      "match_sources": [{{"field": "company_products", "value": "IoT"}}]
    }}
  ]
}}
```"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    patch_intent_llm(monkeypatch, fake_intent)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_provider", "openai")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.openai_generate_text", fake_rerank)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.gemini_generate_text", fake_rerank)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="pro")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "誰認識做 IOT的？", "search_scope": "network"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "COMPLETED", body
        public = [r for r in body["results"] if r["source_pool"] == "public_directory"]
        assert public
        assert public[0]["stub_preview"]["display_name"] == "Ting Hsieh"


@pytest.mark.asyncio
async def test_trgm_on_iot_keyword_finds_ting():
    from sqlalchemy import select

    from app.ai.pipelines.search_intent import parse_intent
    from app.models.public_business_stub import PublicBusinessStub
    from app.modules.m5_search.retrieval import retrieve_public_candidates

    async with async_session_factory() as db:
        stub = (
            await db.execute(
                select(PublicBusinessStub).where(
                    PublicBusinessStub.display_name == "Ting Hsieh",
                    PublicBusinessStub.status == "published",
                )
            )
        ).scalar_one_or_none()
        assert stub
        await index_stub(db, stub.id)
        await db.commit()

        intent = await parse_intent("IoT")
        cands, _debug = await retrieve_public_candidates(db, query_text="IoT", intent=intent)
        names = [c.display_name for c in cands]
        assert "Ting Hsieh" in names


@pytest.mark.asyncio
async def test_widened_recall_loads_pool_when_literal_miss():
    from app.ai.schemas.search_rerank import ParsedIntent
    from app.modules.m5_search.retrieval import retrieve_public_candidates

    intent = ParsedIntent(keywords=["zzznomatch999"])
    async with async_session_factory() as db:
        cands, _debug = await retrieve_public_candidates(db, query_text="zzznomatch999", intent=intent)
        assert len(cands) >= 1
        assert any(c.display_name == "Ting Hsieh" for c in cands)
        assert any(c.retrieval_score > 0 for c in cands)
