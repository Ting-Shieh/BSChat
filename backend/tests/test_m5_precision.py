"""M5 Stage 1b: search_precision preference + DDR-101 score contract."""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import async_session_factory
from app.main import app
from app.modules.m3_contacts.index_builder import index_contact
from app.modules.m5_search.precision import (
    precision_rerank_guidance,
    validate_precision_update,
)
from app.modules.m5_search.retrieval import CandidateDoc

_INDEX_TASKS: list[asyncio.Task] = []
_INDEX_ENQUEUED: set[uuid.UUID] = set()


def _mock_retrieve_single(monkeypatch, contact_id: str, **kwargs) -> None:
    cid = uuid.UUID(contact_id)
    doc = CandidateDoc(
        contact_id=cid,
        display_name=kwargs.get("display_name", "Precision Test"),
        company_name=kwargs.get("company_name", "Acme Corp"),
        title=kwargs.get("title", "Engineer"),
        responsibility_scope=kwargs.get("responsibility_scope"),
        responsibility_confidence=None,
        source_label=None,
        review_status="pending_review",
        phones=[],
        emails=[],
        image_url=None,
        company_products=kwargs.get("company_products", []),
        products_confidence=None,
        search_text=kwargs.get("search_text", "Precision Test Acme Corp"),
        retrieval_score=float(kwargs.get("retrieval_score", 0.5)),
    )

    async def fake_retrieve(db, user_id, query_text, intent, limit=None):
        return [doc], None

    monkeypatch.setattr("app.modules.m5_search.service.retrieve_candidates", fake_retrieve)


async def _login(client: AsyncClient, *, plan_tier: str = "free") -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={
            "email": f"precision-{uuid.uuid4()}@example.com",
            "display_name": "Precision Test",
            "plan_tier": plan_tier,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _sync_index(monkeypatch):
    async def _index_now(contact_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await index_contact(db, contact_id)
            await db.commit()

    def enqueue(contact_id: uuid.UUID) -> None:
        if contact_id in _INDEX_ENQUEUED:
            return
        _INDEX_ENQUEUED.add(contact_id)
        _INDEX_TASKS.append(asyncio.create_task(_index_now(contact_id)))

    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_index", enqueue)
    monkeypatch.setattr("app.workers.tasks.contact_index.enqueue_contact_index", enqueue)


async def _flush_index_queue() -> None:
    if _INDEX_TASKS:
        await asyncio.gather(*_INDEX_TASKS)
        _INDEX_TASKS.clear()
    _INDEX_ENQUEUED.clear()


def _noop_enrich(monkeypatch):
    monkeypatch.setattr("app.modules.m3_contacts.upsert.dispatch_company_enrich", lambda *a, **k: None)
    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_inference", lambda *a, **k: None)


async def _seed_contact(client: AsyncClient, headers: dict) -> str:
    vcard = """BEGIN:VCARD
VERSION:3.0
FN:Precision Test
ORG:Acme Corp
TITLE:Engineer
TEL:0911222333
EMAIL:p@test.com
END:VCARD"""
    imp = await client.post(
        "/api/v1/cards/import-qr",
        json={"payload": vcard},
        headers={**headers, "Idempotency-Key": f"prec-{uuid.uuid4()}"},
    )
    assert imp.status_code == 201, imp.text
    card_id = imp.json()["raw_card_id"]
    review = await client.patch(
        f"/api/v1/cards/{card_id}/review",
        headers=headers,
        json={"name": "Precision Test", "company": "Acme Corp", "title": "Engineer", "version": 1},
    )
    assert review.status_code == 200, review.text
    await asyncio.sleep(0.05)
    listed = await client.get("/api/v1/contacts", headers=headers)
    return listed.json()["items"][0]["id"]


def test_validate_precision_free_blocks_exploratory():
    with pytest.raises(ValueError, match="SEARCH_PRECISION_NOT_ALLOWED"):
        validate_precision_update("free", "exploratory")
    assert validate_precision_update("free", "strict") == "strict"
    assert validate_precision_update("pro", "exploratory") == "exploratory"


def test_precision_rerank_guidance_maps_modes():
    assert "STRICT" in precision_rerank_guidance("strict")
    assert "BALANCED" in precision_rerank_guidance("balanced")
    assert "EXPLORATORY" in precision_rerank_guidance("exploratory")


@pytest.mark.asyncio
async def test_me_includes_search_precision():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}
        me = await client.get("/api/v1/me", headers=headers)
        assert me.status_code == 200
        sp = me.json()["search_precision"]
        assert sp["mode"] == "balanced"
        assert sp["can_use_exploratory"] is False


@pytest.mark.asyncio
async def test_free_cannot_set_exploratory():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.patch(
            "/api/v1/me/settings",
            headers=headers,
            json={"search_precision": "exploratory"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "SEARCH_PRECISION_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_free_can_set_strict():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.patch(
            "/api/v1/me/settings",
            headers=headers,
            json={"search_precision": "strict"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["search_precision"]["mode"] == "strict"


@pytest.mark.asyncio
async def test_strict_precision_empty_when_llm_returns_nothing(monkeypatch):
    """Strict mode: EMPTY when LLM returns no results (prompt-driven, not score filter)."""
    _noop_enrich(monkeypatch)
    _sync_index(monkeypatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}
        contact_id = await _seed_contact(client, headers)
        await _flush_index_queue()

        async def fake_intent(prompt: str, **kwargs):
            return """```json
{"products": [], "roles": [], "events": [], "regions": [], "keywords": ["xyz"],
 "hard_roles": [], "hard_companies": [], "hard_products": []}
```"""

        async def fake_rerank(prompt: str, **kwargs):
            assert "STRICT" in prompt
            return """```json
{"results": []}
```"""

        monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
        monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
        monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_intent)
        monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_use_mock", False)
        monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.gemini_api_key", "test-key")
        monkeypatch.setattr("app.ai.pipelines.search_rerank.gemini_generate_text", fake_rerank)

        _mock_retrieve_single(monkeypatch, contact_id)

        await client.patch(
            "/api/v1/me/settings",
            headers=headers,
            json={"search_precision": "strict"},
        )

        search = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "找 xyz 不相關", "search_scope": "private"},
        )
        assert search.status_code == 200, search.text
        assert search.json()["status"] == "EMPTY"
        assert search.json()["empty_state"]["search_precision"] == "strict"
        assert search.json()["empty_state"]["precision_hint"]


@pytest.mark.asyncio
async def test_balanced_keeps_semantic_match_below_old_threshold(monkeypatch):
    """DDR-101: match_score 0.48 must not be dropped by server-side filter."""
    _noop_enrich(monkeypatch)
    _sync_index(monkeypatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}
        contact_id = await _seed_contact(client, headers)
        await _flush_index_queue()

        async def fake_intent(prompt: str, **kwargs):
            return """```json
{"products": ["IoT"], "roles": [], "events": [], "regions": [], "keywords": ["IoT"],
 "hard_roles": [], "hard_companies": [], "hard_products": []}
```"""

        async def fake_rerank(prompt: str, **kwargs):
            return f"""```json
{{
  "results": [
    {{
      "contact_id": "{contact_id}",
      "match_score": 0.48,
      "match_reason": "索引含 IoT 相關描述",
      "match_sources": [{{"field": "company_name", "value": "Acme Corp"}}]
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

        _mock_retrieve_single(monkeypatch, contact_id, retrieval_score=0.08)

        search = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "誰認識做 IoT 的？", "search_scope": "private"},
        )
        assert search.status_code == 200, search.text
        body = search.json()
        assert body["status"] == "COMPLETED"
        assert body["results"][0]["match_score"] == pytest.approx(0.48)


@pytest.mark.asyncio
async def test_no_retrieval_fallback_when_no_match(monkeypatch):
    """DDR-99: no synthetic 0.35 results when rerank returns nothing."""
    _noop_enrich(monkeypatch)
    _sync_index(monkeypatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}
        contact_id = await _seed_contact(client, headers)
        await _flush_index_queue()

        async def fake_intent(prompt: str, **kwargs):
            return """```json
{"products": [], "roles": [], "events": [], "regions": [], "keywords": ["nomatch"],
 "hard_roles": [], "hard_companies": [], "hard_products": []}
```"""

        async def fake_rerank(prompt: str, **kwargs):
            return """```json
{"results": []}
```"""

        monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
        monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
        monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_intent)
        monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_use_mock", False)
        monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.gemini_api_key", "test-key")
        monkeypatch.setattr("app.ai.pipelines.search_rerank.gemini_generate_text", fake_rerank)

        _mock_retrieve_single(monkeypatch, contact_id)

        search = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "完全找不到的人", "search_scope": "private"},
        )
        assert search.status_code == 200, search.text
        body = search.json()
        assert body["status"] == "EMPTY"
        assert body.get("degraded") is False
        assert body["empty_state"]["reason"] == "NO_MATCH"


@pytest.mark.asyncio
async def test_search_debug_payload_when_enabled(monkeypatch):
    _noop_enrich(monkeypatch)
    _sync_index(monkeypatch)
    monkeypatch.setattr("app.modules.m5_search.service._search_debug_enabled", lambda: True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        headers = {"Authorization": f"Bearer {token}"}
        contact_id = await _seed_contact(client, headers)
        await _flush_index_queue()

        async def fake_intent(prompt: str, **kwargs):
            return """```json
{"products": ["IoT"], "roles": [], "events": [], "regions": [], "keywords": ["IoT"],
 "hard_roles": [], "hard_companies": [], "hard_products": [], "semantic_query": "IoT 物聯網"}
```"""

        async def fake_rerank(prompt: str, **kwargs):
            return f"""```json
{{"results": [{{"contact_id": "{contact_id}", "match_score": 0.72,
 "match_reason": "測試", "match_sources": []}}]}}
```"""

        monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
        monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
        monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_intent)
        monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_use_mock", False)
        monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.gemini_api_key", "test-key")
        monkeypatch.setattr("app.ai.pipelines.search_rerank.gemini_generate_text", fake_rerank)

        from app.modules.m5_search.hybrid import PoolRetrievalDebug, RetrievalCandidateDebug

        cid = uuid.UUID(contact_id)
        doc = CandidateDoc(
            contact_id=cid,
            display_name="Precision Test",
            company_name="Acme Corp",
            title="Engineer",
            responsibility_scope=None,
            responsibility_confidence=None,
            source_label=None,
            review_status="pending_review",
            phones=[],
            emails=[],
            image_url=None,
            company_products=[],
            products_confidence=None,
            search_text="Precision Test Acme Corp IoT",
            retrieval_score=0.5,
        )
        pool_debug = PoolRetrievalDebug(
            pool="private",
            lexical_query="IoT",
            semantic_query="IoT 物聯網",
            ts_hits=1,
            trgm_extra_hits=0,
            vector_hits=1,
            widened=False,
            top_candidates=[
                RetrievalCandidateDebug(id=contact_id, label="Precision Test", retrieval_score=0.5)
            ],
        )

        async def fake_retrieve(db, user_id, query_text, intent, limit=None):
            return [doc], pool_debug

        monkeypatch.setattr("app.modules.m5_search.service.retrieve_candidates", fake_retrieve)

        search = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "誰認識做 IoT 的？", "search_scope": "private"},
        )
        assert search.status_code == 200, search.text
        body = search.json()
        debug = body.get("debug")
        assert debug is not None
        assert debug["intent_prompt_version"] == "v3"
        assert debug["rerank_prompt_version"] == "v5"
        assert debug["private"]["pool"] == "private"
        assert debug["rerank_input_count"] >= 1
        assert "IoT" in debug["parsed_intent"].get("keywords", [])
