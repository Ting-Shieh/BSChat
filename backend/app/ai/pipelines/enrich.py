import json
import time

import httpx

from app.ai.schemas.enrich_output import EnrichOutput
from app.core.config import get_settings

settings = get_settings()

PROMPT_VERSION = "v1"
EXTRACT_PROMPT = """Extract company business information from the webpage text below.
Company name: {company_name}

Return JSON only:
{{
  "main_products": ["product or service 1", "..."],  // 1-5 items, each <= 80 chars, Traditional Chinese preferred
  "summary": "one sentence company summary or null",
  "industry_tags": ["tag1"],
  "overall_confidence": 0.0-1.0,
  "fields_provenance": {{
    "main_products": {{ "source_urls": ["..."], "confidence": 0.0-1.0 }}
  }}
}}

Webpage text:
{text}
"""


def _mock_enrich(company_name: str) -> EnrichOutput:
    lower = company_name.lower()
    if "amazon" in lower or "亞馬遜" in company_name:
        return EnrichOutput(
            main_products=["雲端運算 (AWS)", "企業雲端解決方案", "AI 與機器學習服務"],
            summary="亞馬遜雲端服務提供可擴展的雲端運算平台與企業解決方案。",
            industry_tags=["雲端運算", "SaaS"],
            overall_confidence=0.82,
            fields_provenance={
                "main_products": {"source_urls": ["https://aws.amazon.com"], "confidence": 0.82}
            },
        )
    return EnrichOutput(
        main_products=["企業解決方案", "專業服務"],
        summary=f"{company_name} 提供相關產品與服務。",
        industry_tags=["B2B"],
        overall_confidence=0.55,
        fields_provenance={"main_products": {"source_urls": [], "confidence": 0.55}},
    )


def _parse_json(text: str) -> EnrichOutput:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text.strip())
    return EnrichOutput.model_validate(parsed)


async def extract_company_info(
    company_name: str,
    page_text: str,
    source_urls: list[str],
) -> tuple[EnrichOutput, int, str, str]:
    if settings.enrich_use_mock or not page_text.strip():
        if settings.enrich_use_mock:
            return _mock_enrich(company_name), 0, "mock", PROMPT_VERSION
        return EnrichOutput(overall_confidence=0.0), 0, "none", PROMPT_VERSION

    provider = settings.effective_enrich_provider
    prompt = EXTRACT_PROMPT.format(company_name=company_name, text=page_text[:12000])
    start = time.perf_counter()

    if provider == "gemini":
        if not settings.gemini_api_key:
            return _mock_enrich(company_name), 0, "mock", PROMPT_VERSION
        model = settings.gemini_enrich_model
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={settings.gemini_api_key}"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        output = _parse_json(text)
        duration_ms = int((time.perf_counter() - start) * 1000)
        if not output.fields_provenance.get("main_products", {}).get("source_urls"):
            output.fields_provenance.setdefault("main_products", {})["source_urls"] = source_urls
        return output, duration_ms, model, PROMPT_VERSION

    if provider == "claude" and settings.anthropic_api_key:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.enrich_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text
        output = _parse_json(text)
        duration_ms = int((time.perf_counter() - start) * 1000)
        if not output.fields_provenance.get("main_products", {}).get("source_urls"):
            output.fields_provenance.setdefault("main_products", {})["source_urls"] = source_urls
        return output, duration_ms, settings.enrich_model, PROMPT_VERSION

    return _mock_enrich(company_name), 0, "mock", PROMPT_VERSION
