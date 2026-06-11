"""Public web lookup for a user-provided LinkedIn profile URL (interim until official API)."""

import json
import re
from dataclasses import dataclass

from app.ai.gemini_client import gemini_generate_with_google_search
from app.ai.pipelines.person_enrich import PersonCandidate
from app.core.config import get_settings

settings = get_settings()

PROMPT_VERSION = "v1"

WEB_LOOKUP_PROMPT = """你是 B2B 人脈助手。使用者提供了以下 LinkedIn 個人頁連結，請**僅**從公開網路搜尋結果中，整理與「這個連結對應的個人」有關的職場公開資訊。

LinkedIn URL（必須對應此連結，不要搜尋其他同名的人）：
{linkedin_url}

名片線索（僅供核對，可能不完整）：
- 姓名：{name}
- 公司：{company_name}
- 職稱：{title}

規則：
- 只使用搜尋引擎可索引的公開摘要；不要臆測、不要寫具體客戶名
- 若無法確認結果對應此 URL/此人，confidence 必須 < 0.5
- 輸出 JSON only：
{{
  "headline": "一句話現職描述（無則空字串）",
  "summary": "2-4 句公開摘要，含職責/領域線索",
  "confidence": 0.0-1.0,
  "matched_url": true
}}

matched_url 僅在搜尋結果明確對應此 LinkedIn URL 時為 true。
"""


@dataclass
class WebProfileLookup:
    headline: str
    summary: str
    confidence: float
    matched_url: bool
    cited_urls: list[str]


def extract_linkedin_vanity(url: str) -> str | None:
    match = re.search(r"linkedin\.com/in/([^/?#]+)", url, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip("/").lower()


def _normalize_linkedin_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _parse_lookup_json(text: str) -> WebProfileLookup | None:
    cleaned = text.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    try:
        parsed = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return None
    headline = str(parsed.get("headline") or "").strip()
    summary = str(parsed.get("summary") or "").strip()
    if not summary and not headline:
        return None
    return WebProfileLookup(
        headline=headline,
        summary=summary or headline,
        confidence=float(parsed.get("confidence", 0.0)),
        matched_url=bool(parsed.get("matched_url")),
        cited_urls=[],
    )


def _grounding_matches_vanity(vanity: str, urls: list[str]) -> bool:
    needle = vanity.lower()
    for raw in urls:
        lower = raw.lower()
        if "linkedin.com" in lower and needle in lower:
            return True
    return False


def _web_fallback_enabled() -> bool:
    if not settings.person_linkedin_web_fallback:
        return False
    if settings.person_enrich_use_mock:
        return False
    return bool(settings.gemini_api_key)


async def fetch_profile_via_web_search(
    url: str,
    *,
    name: str | None = None,
    title: str | None = None,
    company_name: str | None = None,
) -> PersonCandidate | None:
    """Use Gemini + Google Search grounding for a single known LinkedIn URL."""
    if not _web_fallback_enabled():
        return None

    linkedin_url = _normalize_linkedin_url(url)
    vanity = extract_linkedin_vanity(linkedin_url)
    if not vanity:
        return None

    prompt = WEB_LOOKUP_PROMPT.format(
        linkedin_url=linkedin_url,
        name=name or "（未知）",
        company_name=company_name or "（未知）",
        title=title or "（未知）",
    )

    try:
        text, grounding_urls = await gemini_generate_with_google_search(
            prompt,
            model=settings.gemini_person_model,
            timeout=45.0,
        )
    except Exception:
        return None

    lookup = _parse_lookup_json(text)
    if not lookup:
        return None

    url_matched = lookup.matched_url or _grounding_matches_vanity(vanity, grounding_urls)
    if not url_matched or lookup.confidence < 0.35:
        return None

    match_score = 1.0 if url_matched and lookup.confidence >= 0.55 else 0.85
    return PersonCandidate(
        linkedin_url=linkedin_url,
        headline=lookup.headline or None,
        summary=lookup.summary,
        match_score=match_score,
        match_inputs={
            "source": "web_search",
            "vanity": vanity,
            "lookup_confidence": lookup.confidence,
            "cited_urls": grounding_urls[:5],
        },
        source_type="web_search",
    )
