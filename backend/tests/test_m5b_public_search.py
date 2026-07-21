"""M5b: Pro cross-pool search (public directory)."""

import asyncio
import uuid

import pytest

from intent_llm_testutil import patch_intent_llm
from httpx import ASGITransport, AsyncClient

from app.core.db import async_session_factory
from app.main import app
from app.modules.m11_public_directory.index_builder import index_stub


async def _login(
    client: AsyncClient,
    *,
    email: str | None = None,
    plan_tier: str = "pro",
    seed_org: str | None = None,
) -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={
            "email": email or f"m5b-{uuid.uuid4()}@example.com",
            "display_name": "M5b Test",
            "plan_tier": plan_tier,
            "seed_org": seed_org,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _sync_public_index(monkeypatch):
    async def _index_now(stub_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await index_stub(db, stub_id)

    def enqueue_index(stub_id: uuid.UUID) -> None:
        asyncio.get_running_loop().create_task(_index_now(stub_id))

    monkeypatch.setattr(
        "app.modules.m11_public_directory.service.enqueue_stub_index",
        enqueue_index,
    )
    monkeypatch.setattr(
        "app.workers.tasks.public_directory_index.enqueue_stub_index",
        enqueue_index,
    )


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
            stub_id = stub.id
        await db.commit()
    assert stub_id is not None
    return stub_id


def _mock_public_search_llm(monkeypatch, stub_id: uuid.UUID) -> None:
    from app.modules.m5_search.retrieval import PublicCandidateDoc

    sid = str(stub_id)
    pub = PublicCandidateDoc(
        stub_id=stub_id,
        org_id=uuid.uuid4(),
        org_name="Acme Demo",
        display_name="張業務",
        company_name="Acme Industrial",
        title="業務經理",
        responsibility_keywords=["嵌入式", "工業電腦"],
        product_keywords=["嵌入式系統", "工業電腦"],
        external_card_url="https://example.com/card",
        search_text="Acme Industrial 嵌入式 工業電腦",
        retrieval_score=0.7,
    )

    async def fake_retrieve_public(db, query_text, intent, limit=None):
        return [pub], None

    async def fake_intent(prompt: str, **kwargs):
        return """```json
{"products": ["工業電腦", "嵌入式"], "roles": [], "events": [], "regions": [],
 "keywords": ["工業電腦", "嵌入式"], "hard_roles": [], "hard_companies": [], "hard_products": []}
```"""

    async def fake_rerank(prompt: str, **kwargs):
        return f"""```json
{{
  "results": [
    {{
      "contact_id": "{sid}",
      "match_score": 0.88,
      "match_reason": "公開商務 · Acme Demo；張業務 · Acme Industrial，產品含嵌入式與工業電腦",
      "match_sources": [{{"field": "company_products", "value": "嵌入式系統"}}]
    }}
  ]
}}
```"""

    monkeypatch.setattr("app.modules.m5_search.service.retrieve_public_candidates", fake_retrieve_public)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    patch_intent_llm(monkeypatch, fake_intent)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_provider", "openai")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.openai_generate_text", fake_rerank)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.gemini_generate_text", fake_rerank)


@pytest.mark.asyncio
async def test_m5b_pro_network_search(monkeypatch):
    _sync_public_index(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(
            client,
            email=f"acme-publisher-{uuid.uuid4()}@example.com",
            plan_tier="enterprise",
            seed_org="acme-demo",
        )
        stub_id = await _ensure_published_indexed()
        _mock_public_search_llm(monkeypatch, stub_id)

        pro_token = await _login(client, plan_tier="pro")
        headers = {"Authorization": f"Bearer {pro_token}"}

        resp = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "誰做工業電腦或嵌入式的", "search_scope": "network"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "COMPLETED"
        assert body["result_count"] >= 1
        public = [r for r in body["results"] if r["source_pool"] == "public_directory"]
        assert public
        assert public[0]["stub_id"]
        assert public[0]["external_card_url"]
        assert public[0]["contact_preview"] is None
        assert "公開商務" in public[0]["match_reason"]


@pytest.mark.asyncio
async def test_m5b_free_network_forbidden_when_trial_exhausted():
    from sqlalchemy import select

    from app.models.user import User

    email = f"free-exhausted-{uuid.uuid4()}@example.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, email=email, plan_tier="free")
        async with async_session_factory() as db:
            user = (await db.execute(select(User).where(User.email == email))).scalar_one()
            await db.refresh(user, attribute_names=["entitlement"])
            user.entitlement.public_recommend_used_lifetime = 2
            await db.commit()
        resp = await client.post(
            "/api/v1/search/queries",
            headers={"Authorization": f"Bearer {token}"},
            json={"query_text": "工業電腦", "search_scope": "network"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "PUBLIC_RECOMMEND_TRIAL_EXHAUSTED"


@pytest.mark.asyncio
async def test_m5b_all_scope_merges_pools(monkeypatch):
    _sync_public_index(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(
            client,
            email=f"acme-publisher2-{uuid.uuid4()}@example.com",
            plan_tier="enterprise",
            seed_org="acme-demo",
        )
        stub_id = await _ensure_published_indexed()
        _mock_public_search_llm(monkeypatch, stub_id)

        pro_token = await _login(client, plan_tier="pro")
        headers = {"Authorization": f"Bearer {pro_token}"}

        resp = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "嵌入式", "search_scope": "all"},
        )
        assert resp.status_code == 200, resp.text
        pools = {r["source_pool"] for r in resp.json().get("results", [])}
        assert "public_directory" in pools
