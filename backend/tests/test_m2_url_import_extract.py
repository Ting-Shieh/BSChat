import pytest

from app.ai.pipelines import url_import_extract as extract_mod


MYSC_SNIPPET = """
<div>賴昀君</div><div>Aply Lai</div>
<div>資深專案經理</div><div>威剛科技股份有限公司</div>
<a href="mailto:aply_lai@adata.com">email</a>
<a href="tel:+886-2-8228-0886">phone</a>
<meta itemprop="image" content="https://cdn.example.com/card.jpg"/>
"""


@pytest.mark.asyncio
async def test_llm_extract_from_html(monkeypatch):
    async def fake_gemini(prompt: str, **kwargs):
        assert "賴昀君" in prompt or "aply_lai@adata.com" in prompt
        return """```json
{
  "name": "賴昀君",
  "company": "威剛科技股份有限公司",
  "title": "資深專案經理",
  "phones": ["+886282280886"],
  "emails": ["aply_lai@adata.com"],
  "address": null,
  "website": "https://mysc.cc/company/demo",
  "image_url": "https://cdn.example.com/card.jpg"
}
```"""

    monkeypatch.setattr(extract_mod, "gemini_generate_text", fake_gemini)
    result = await extract_mod.extract_contact_from_html(
        MYSC_SNIPPET,
        "https://mysc.cc/company/demo",
    )
    assert result["fields"]["name"] == "賴昀君"
    assert result["resolver_type"] == "llm_html"
    assert result["image_url"] == "https://cdn.example.com/card.jpg"
