import pytest

from app.ai.pipelines.search_intent import (
    _parse_intent_fallback,
    parse_intent,
    parse_intent_result,
)


@pytest.mark.asyncio
async def test_parse_intent_openai_roles(monkeypatch):
    async def fake_chat(messages, **kwargs):
        assert messages[0]["role"] == "system"
        assert "intent_kind" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert "飯店相關推薦人" in messages[1]["content"]
        return """{
  "intent_kind": "find_people",
  "products": ["飯店"],
  "roles": [],
  "events": [],
  "regions": [],
  "keywords": ["飯店", "推薦", "度假"],
  "semantic_query": "找飯店相關推薦人",
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_skip_intent_parse", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_provider", "openai")
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.openai_chat", fake_chat)

    intent = await parse_intent("飯店相關推薦人")
    assert intent.intent_kind == "find_people"
    assert "飯店" in intent.keywords
    assert intent.hard_companies == []


@pytest.mark.asyncio
async def test_parse_intent_browse_public(monkeypatch):
    async def fake_chat(messages, **kwargs):
        assert "公開商務有誰" in messages[1]["content"]
        return """{
  "intent_kind": "browse_public",
  "products": [],
  "roles": [],
  "events": [],
  "regions": [],
  "keywords": [],
  "semantic_query": "",
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_skip_intent_parse", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_provider", "openai")
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.openai_chat", fake_chat)

    intent = await parse_intent("公開商務有誰")
    assert intent.intent_kind == "browse_public"


@pytest.mark.asyncio
async def test_followup_cloud_is_find_people(monkeypatch):
    async def fake_chat(messages, **kwargs):
        user = messages[1]["content"]
        assert "公開池有誰" in user
        assert "有雲端相關業者嗎" in user
        return """{
  "intent_kind": "find_people",
  "products": ["雲端"],
  "roles": [],
  "events": [],
  "regions": [],
  "keywords": ["雲端", "業者"],
  "semantic_query": "找雲端相關業者",
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_skip_intent_parse", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_provider", "openai")
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.openai_chat", fake_chat)

    intent = await parse_intent("有雲端相關業者嗎？", prior_turns=["公開池有誰？"])
    assert intent.intent_kind == "find_people"
    assert "雲端" in intent.keywords or "雲端" in intent.products


@pytest.mark.asyncio
async def test_llm_fail_no_keyword_browse(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("403")

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_skip_intent_parse", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_provider", "openai")
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.openai_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.openai_chat", boom)

    result = await parse_intent_result("公開商務有誰")
    assert result.llm_ok is False
    # Must not invent browse via keyword rules when LLM is down
    assert result.intent.intent_kind == "find_people"


def test_fallback_splits_chinese_without_domain_lists():
    intent = _parse_intent_fallback("飯店相關推薦人")
    assert "飯店" in intent.keywords
    assert intent.intent_kind == "find_people"
    assert intent.hard_companies == []
    assert intent.products == []


def test_fallback_never_browse():
    intent = _parse_intent_fallback("公開商務有誰")
    assert intent.intent_kind == "find_people"
