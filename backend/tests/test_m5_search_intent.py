import pytest

from app.ai.pipelines.search_intent import _parse_intent_fallback, parse_intent
from app.ai.schemas.search_rerank import ParsedIntent


@pytest.mark.asyncio
async def test_parse_intent_gemini(monkeypatch):
    async def fake_gemini(prompt: str, **kwargs):
        assert "飯店相關推薦人" in prompt
        return """```json
{
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

    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.search_use_mock", False)
    monkeypatch.setattr("app.ai.pipelines.search_intent.settings.gemini_api_key", "test-key")
    monkeypatch.setattr("app.ai.pipelines.search_intent.gemini_generate_text", fake_gemini)

    intent = await parse_intent("飯店相關推薦人")
    assert "飯店" in intent.keywords
    assert intent.hard_companies == []


def test_fallback_splits_chinese_without_domain_lists():
    intent = _parse_intent_fallback("飯店相關推薦人")
    assert "飯店" in intent.keywords
    assert intent.hard_companies == []
    assert intent.products == []
