import pytest

from app.ai.schemas.website_discovery_output import WebsiteCandidate
from app.modules.m6_enrichment.website_discovery import (
    _heuristic_domain_candidates,
    _slug_candidates,
    _website_from_email,
    discover_website,
)


def test_slug_from_parenthetical_english():
    slugs = _slug_candidates("某某公司 (ADATA Technology Co., Ltd.)")
    assert "adata" in slugs


def test_heuristic_domain_candidates_from_english_slug():
    urls = _heuristic_domain_candidates("某某公司 (ADATA Technology Co., Ltd.)")
    assert any("adata.com" in u for u in urls)


def test_website_from_email_adata():
    assert _website_from_email("aply_lai@adata.com") == "https://www.adata.com"
    assert _website_from_email("user@gmail.com") is None


@pytest.mark.asyncio
async def test_discover_website_uses_ai_candidates(monkeypatch):
    async def fake_infer(_name, *, contact_email=None):
        return (
            [WebsiteCandidate(url="https://www.adata.com", confidence=0.95)],
            "gemini-2.5-flash",
            "v1",
        )

    async def fake_probe(urls):
        return urls[0] if urls else None

    monkeypatch.setattr(
        "app.modules.m6_enrichment.website_discovery.infer_company_website_candidates",
        fake_infer,
    )
    monkeypatch.setattr(
        "app.modules.m6_enrichment.website_discovery._probe_first_reachable",
        fake_probe,
    )
    url = await discover_website("威剛科技股份有限公司", contact_email="aply_lai@adata.com")
    assert url == "https://www.adata.com"


@pytest.mark.asyncio
async def test_discover_website_ai_pipeline_parsing(monkeypatch):
    from app.ai.pipelines import website_discovery as pipeline

    async def fake_search(prompt: str, **kwargs):
        assert "威剛科技股份有限公司" in prompt
        return (
            '{"candidates":[{"url":"https://www.adata.com","confidence":0.95}]}',
            ["https://www.adata.com/about"],
        )

    monkeypatch.setattr(pipeline.settings, "enrich_use_mock", False)
    monkeypatch.setattr(pipeline.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(pipeline, "gemini_generate_with_google_search", fake_search)
    candidates, model, _ = await pipeline.infer_company_website_candidates("威剛科技股份有限公司")
    assert model == pipeline.settings.gemini_enrich_model
    assert candidates[0].url == "https://www.adata.com"
