"""M3.5 person enrichment pipeline: profile lookup + LLM scope summarize.

Mock-first, provider-pluggable (mirrors M3/M6 patterns). No self-built scraper.
"""

import json
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.ai.gemini_client import gemini_generate_text
from app.ai.schemas.person_scope_output import PersonScopeOutput
from app.core.config import get_settings

settings = get_settings()

PROMPT_VERSION = "v1"

SUMMARIZE_PROMPT = """你是 B2B 人脈助手。根據此人的職場公開資料片段，整理出「可能負責的業務範圍」。

姓名：{name}
名片職稱：{title}
公司：{company_name}
公開資料 headline：{headline}
公開資料摘要：{summary}

規則：
- 輸出 JSON only：{{ "scope": "...", "confidence": 0.0-1.0 }}
- scope 使用繁體中文，1-2 句，必須以「可能負責」開頭
- 以公開資料為主、名片職稱為輔；不要臆測具體客戶名；不要寫在職狀態
- 公開資料與名片明顯不一致或資訊不足時，confidence 必須 < 0.75
"""


@dataclass
class PersonCandidate:
    linkedin_url: str | None
    headline: str | None
    summary: str | None
    match_score: float
    match_inputs: dict = field(default_factory=dict)
    source_type: str = "people_api"


def _sim(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def compute_match_score(
    *,
    name_sim: float,
    company_sim: float,
    title_sim: float,
) -> float:
    return round(0.4 * name_sim + 0.35 * company_sim + 0.25 * title_sim, 4)


def _mock_search_candidates(
    *, name: str, company_name: str | None, title: str | None
) -> list[PersonCandidate]:
    if not name:
        return []
    name_sim = 1.0
    company_sim = 1.0 if company_name else 0.3
    title_sim = 0.85 if title else 0.4
    score = compute_match_score(name_sim=name_sim, company_sim=company_sim, title_sim=title_sim)
    headline_parts = [p for p in [title, company_name] if p]
    headline = " @ ".join(headline_parts) if headline_parts else f"{name}"
    return [
        PersonCandidate(
            linkedin_url=None,
            headline=headline,
            summary=f"公開職場資料：{headline}。",
            match_score=score,
            match_inputs={"name_sim": name_sim, "company_sim": company_sim, "title_sim": title_sim},
            source_type="people_api",
        )
    ]


def _person_use_mock() -> bool:
    if settings.person_enrich_use_mock:
        return True
    return settings.effective_person_enrich_provider == "mock"


def person_search_is_mock() -> bool:
    """True until official LinkedIn profile lookup is configured."""
    return settings.person_search_provider == "mock"


async def _fetch_by_url_linkedin(
    url: str, *, title: str | None, company_name: str | None
) -> PersonCandidate | None:
    """Official LinkedIn API integration point — implement when credentials are available."""
    _ = (url, title, company_name)
    return None


async def fetch_by_url(
    url: str,
    *,
    name: str | None = None,
    title: str | None = None,
    company_name: str | None = None,
) -> PersonCandidate | None:
    """Resolve a profile by direct LinkedIn URL. None = provider unavailable or not found."""
    provider = settings.person_search_provider
    candidate: PersonCandidate | None = None

    if provider == "linkedin":
        candidate = await _fetch_by_url_linkedin(
            url, title=title, company_name=company_name
        )

    if candidate is None:
        from app.ai.pipelines.person_linkedin_web import fetch_profile_via_web_search

        candidate = await fetch_profile_via_web_search(
            url,
            name=name,
            title=title,
            company_name=company_name,
        )

    return candidate


async def search_people(
    *, name: str, company_name: str | None = None, title: str | None = None
) -> list[PersonCandidate]:
    """Find candidate profiles by name + company (+ title). Returns 0..N candidates."""
    if person_search_is_mock():
        return []
    if settings.person_search_provider == "linkedin":
        return []
    return _mock_search_candidates(name=name, company_name=company_name, title=title)


def build_card_inference_candidate(
    *, name: str, company_name: str | None = None, title: str | None = None
) -> PersonCandidate:
    """Fallback when LinkedIn cannot be resolved — must NOT be labeled as LinkedIn in UI."""
    headline_parts = [p for p in [title, company_name] if p]
    headline = " @ ".join(headline_parts) if headline_parts else (name or "（未知）")
    return PersonCandidate(
        linkedin_url=None,
        headline=headline,
        summary=f"名片欄位：{headline}。",
        match_score=1.0,
        match_inputs={"source": "card_inference"},
        source_type="card_inference",
    )


def _parse_json(text: str) -> PersonScopeOutput:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text.strip())
    scope = str(parsed.get("scope", "")).strip()
    if scope and not scope.startswith("可能負責"):
        scope = f"可能負責{scope.lstrip('可能负责').lstrip('可能負責')}"
    return PersonScopeOutput(scope=scope, confidence=float(parsed.get("confidence", 0.0)))


def _mock_summarize(candidate: PersonCandidate, *, title: str | None, company_name: str | None) -> PersonScopeOutput:
    headline = (candidate.headline or "").lower()
    if "oem" in headline:
        return PersonScopeOutput(scope="可能負責 OEM 通路與大客戶開發", confidence=0.82)
    if any(k in headline for k in ("sales", "業務", "通路")):
        return PersonScopeOutput(scope="可能負責業務開發與通路經營", confidence=0.8)
    if any(k in headline for k in ("fae", "engineer", "工程", "技術")):
        return PersonScopeOutput(scope="可能負責技術支援與客戶導入方案", confidence=0.78)
    base = company_name or title or "相關業務"
    return PersonScopeOutput(scope=f"可能負責與{base}相關的業務範圍", confidence=0.76)


async def summarize_person_scope(
    candidate: PersonCandidate, *, name: str, title: str | None, company_name: str | None
) -> tuple[PersonScopeOutput, str, str]:
    """Returns (output, model, prompt_version)."""
    if _person_use_mock():
        return _mock_summarize(candidate, title=title, company_name=company_name), "mock", PROMPT_VERSION

    prompt = SUMMARIZE_PROMPT.format(
        name=name or "（未知）",
        title=title or "（未知）",
        company_name=company_name or "（未知）",
        headline=candidate.headline or "（無）",
        summary=candidate.summary or "（無）",
    )
    provider = settings.effective_person_enrich_provider
    _start = time.perf_counter()

    if provider == "gemini":
        text = await gemini_generate_text(prompt, model=settings.gemini_person_model)
        return _parse_json(text), settings.gemini_person_model, PROMPT_VERSION

    if provider == "claude" and settings.anthropic_api_key:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.person_enrich_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json(msg.content[0].text), settings.person_enrich_model, PROMPT_VERSION

    return _mock_summarize(candidate, title=title, company_name=company_name), "mock", PROMPT_VERSION
