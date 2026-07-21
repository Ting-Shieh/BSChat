import pytest

from app.ai.pipelines.search_intent import (
    _offline_meta_intent,
    _parse_intent_fallback,
    parse_intent,
    parse_intent_result,
)


@pytest.mark.asyncio
async def test_parse_intent_gemini(monkeypatch):
    async def fake_gemini(prompt: str, **kwargs):
        assert "飯店相關推薦人" in prompt
        return """```json
{
  "intent_kind": "find_people",
  "products": ["飯店"],
  "roles": [],
  "events": [],
  "regions": [],
  "keywords": ["飯店", "推薦", "度假"],
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}
```"""

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_skip_intent_parse", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_gemini)

    intent = await parse_intent("飯店相關推薦人")
    assert intent.intent_kind == "find_people"
    assert "飯店" in intent.keywords
    assert intent.hard_companies == []


@pytest.mark.asyncio
async def test_parse_intent_browse_public(monkeypatch):
    async def fake_gemini(prompt: str, **kwargs):
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
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_gemini)

    intent = await parse_intent("公開商務有誰")
    assert intent.intent_kind == "browse_public"


@pytest.mark.asyncio
async def test_llm_fail_offline_browse(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("403 leaked")

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_skip_intent_parse", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", boom)

    result = await parse_intent_result("公開商務有誰")
    assert result.llm_ok is False
    assert result.intent.intent_kind == "browse_public"


def test_offline_meta_browse():
    assert _offline_meta_intent("公開商務有誰", None).intent_kind == "browse_public"
    assert _offline_meta_intent("誰做工業電腦", None) is None


def test_fallback_never_browse_without_meta():
    intent = _parse_intent_fallback("公開商務有誰")
    assert intent.intent_kind == "find_people"


def test_fallback_splits_chinese_without_domain_lists():
    intent = _parse_intent_fallback("飯店相關推薦人")
    assert "飯店" in intent.keywords
    assert intent.hard_companies == []
    assert intent.products == []
