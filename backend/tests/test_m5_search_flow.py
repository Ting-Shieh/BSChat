"""M5 search flow integration tests with mocked Gemini."""

import uuid

import pytest

from app.ai.pipelines.search_intent import parse_intent
from app.ai.pipelines.search_rerank import rerank_contacts
from app.modules.m5_search.constraints import filter_rerank_results, satisfies_hard_constraints
from app.modules.m5_search.retrieval import CandidateDoc


@pytest.mark.asyncio
async def test_intent_to_rerank_hotel_flow(monkeypatch):
    async def fake_intent(prompt: str, **kwargs):
        return """```json
{
  "products": ["飯店", "度假"],
  "roles": [],
  "events": [],
  "regions": [],
  "keywords": ["飯店", "推薦", "度假"],
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": ["飯店"]
}
```"""

    async def fake_rerank(prompt: str, **kwargs):
        return """```json
{
  "results": [
    {
      "contact_id": "hotel-id",
      "match_score": 0.92,
      "match_reason": "任職於瓏山林度假飯店，與飯店產業高度相關",
      "match_sources": [
        {"field": "company_name", "value": "瓏山林度假飯店"},
        {"field": "title", "value": "業務經理"}
      ]
    }
  ]
}
```"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_intent)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_rerank.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_rerank.gemini_generate_text", fake_rerank)

    intent = await parse_intent("飯店相關推薦人")
    assert "飯店" in intent.keywords

    cands = [
        {
            "contact_id": "hotel-id",
            "display_name": "游瑞恩",
            "title": "業務經理",
            "company_name": "瓏山林度假飯店",
            "search_text": "游瑞恩 瓏山林度假飯店 業務經理",
            "company_products": ["度假"],
            "review_status": "confirmed",
            "retrieval_score": 0.7,
        }
    ]
    resp, _ = await rerank_contacts("飯店相關推薦人", cands, intent)
    assert len(resp.results) == 1
    assert resp.results[0].match_sources
    assert "飯店" in resp.results[0].match_reason


@pytest.mark.asyncio
async def test_intent_to_filter_aws_architect_flow(monkeypatch):
    pm_id, sa_id = str(uuid.uuid4()), str(uuid.uuid4())

    async def fake_intent(prompt: str, **kwargs):
        return """```json
{
  "products": [],
  "roles": ["架構師"],
  "events": [],
  "regions": [],
  "keywords": ["AWS", "人脈", "架構師"],
  "hard_roles": ["架構師"],
  "hard_companies": ["amazon", "亞馬遜"],
  "hard_products": []
}
```"""

    async def fake_rerank(prompt: str, **kwargs):
        return f"""```json
{{
  "results": [
    {{
      "contact_id": "{pm_id}",
      "match_score": 0.85,
      "match_reason": "在 AWS 任職",
      "match_sources": []
    }},
    {{
      "contact_id": "{sa_id}",
      "match_score": 0.95,
      "match_reason": "資深架構師，符合 AWS 架構師條件",
      "match_sources": [{{"field": "title", "value": "資深架構師"}}]
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

    intent = await parse_intent("從我AWS人脈中找從事架構師的就好")
    assert "架構師" in intent.hard_roles

    cands = [
        {
            "contact_id": pm_id,
            "display_name": "Maggie",
            "title": "Program Manager",
            "company_name": "Amazon Web Services",
            "search_text": "program manager amazon",
            "company_products": [],
            "review_status": "confirmed",
            "retrieval_score": 0.6,
        },
        {
            "contact_id": sa_id,
            "display_name": "王仕榮",
            "title": "資深架構師",
            "company_name": "台灣亞馬遜網路服務有限公司",
            "search_text": "資深架構師 amazon",
            "company_products": ["雲端"],
            "review_status": "confirmed",
            "retrieval_score": 0.7,
        },
    ]
    resp, _ = await rerank_contacts("從我AWS人脈中找從事架構師的就好", cands, intent)

    doc_map = {
        pm_id: CandidateDoc(
            contact_id=uuid.UUID(pm_id),
            display_name="Maggie",
            title="Program Manager",
            company_name="Amazon Web Services",
            search_text="program manager amazon",
            review_status="confirmed",
            retrieval_score=0.6,
            responsibility_scope=None,
            responsibility_confidence=None,
            source_label=None,
            phones=[],
            emails=[],
            image_url=None,
            company_products=[],
            products_confidence=None,
        ),
        sa_id: CandidateDoc(
            contact_id=uuid.UUID(sa_id),
            display_name="王仕榮",
            title="資深架構師",
            company_name="台灣亞馬遜網路服務有限公司",
            search_text="資深架構師 amazon",
            review_status="confirmed",
            retrieval_score=0.7,
            responsibility_scope=None,
            responsibility_confidence=None,
            source_label=None,
            phones=[],
            emails=[],
            image_url=None,
            company_products=[],
            products_confidence=None,
        ),
    }

    filtered = filter_rerank_results(resp.results, doc_map, intent)
    ids = {r.contact_id for r in filtered}
    assert sa_id in ids
    assert pm_id not in ids
    assert satisfies_hard_constraints(doc_map[sa_id], intent)
    assert not satisfies_hard_constraints(doc_map[pm_id], intent)


@pytest.mark.asyncio
async def test_intent_no_match_keywords(monkeypatch):
    async def fake_intent(prompt: str, **kwargs):
        return """```json
{
  "products": [],
  "roles": [],
  "events": [],
  "regions": [],
  "keywords": ["量子計算", "超導體", "奈米機器人"],
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}
```"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_intent)

    intent = await parse_intent("量子計算超導體奈米機器人")
    assert intent.keywords
    assert not intent.hard_roles
