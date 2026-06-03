"""LLM + Google Search grounding for company official website discovery."""

import json
import re
from urllib.parse import urlparse

import httpx

from app.ai.gemini_client import gemini_generate_with_google_search
from app.ai.schemas.website_discovery_output import WebsiteCandidate, WebsiteDiscoveryOutput
from app.core.config import get_settings

settings = get_settings()

PROMPT_VERSION = "v1"

DISCOVERY_PROMPT = """Find the official corporate website for this company.

Company name: {company_name}
{email_hint}

Return JSON only:
{{
  "candidates": [
    {{"url": "https://...", "confidence": 0.0-1.0}}
  ]
}}

Rules:
- Return 1-3 candidate URLs for the company's official homepage (not LinkedIn, Facebook, job boards, news, Wikipedia, or digital business card platforms).
- Prefer https URLs. Taiwan companies often use .com.tw or global .com domains.
- confidence 0.9+ only when you are confident this is the official corporate site.
- If truly unknown, return {{"candidates": []}}.
"""

_BLOCKED_HOST_SUFFIXES = (
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "wikipedia.org",
    "crunchbase.com",
    "findcompany.com.tw",
    "104.com.tw",
    "1111.com.tw",
    "mysc.cc",
    "cakeresume.com",
)


def _parse_json(text: str) -> WebsiteDiscoveryOutput:
    cleaned = text.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    parsed = json.loads(cleaned.strip())
    return WebsiteDiscoveryOutput.model_validate(parsed)


def _normalize_candidate_url(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/') or ''}"


def _is_blocked_host(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return True
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in _BLOCKED_HOST_SUFFIXES)


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        normalized = _normalize_candidate_url(url)
        if not normalized or _is_blocked_host(normalized):
            continue
        key = urlparse(normalized).netloc.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized)
    return out


def _email_hint(contact_email: str | None) -> str:
    if not contact_email or "@" not in contact_email:
        return "Work email: (none)"
    domain = contact_email.rsplit("@", 1)[-1].strip()
    return f"Work email domain hint: {domain}"


async def infer_company_website_candidates(
    company_name: str,
    *,
    contact_email: str | None = None,
) -> tuple[list[WebsiteCandidate], str, str]:
    """Return ranked URL candidates from Gemini + Google Search grounding."""
    if settings.enrich_use_mock or not settings.gemini_api_key:
        return [], "mock", PROMPT_VERSION

    prompt = DISCOVERY_PROMPT.format(
        company_name=company_name.strip(),
        email_hint=_email_hint(contact_email),
    )
    model = settings.gemini_enrich_model

    try:
        text, grounding_urls = await gemini_generate_with_google_search(
            prompt,
            model=model,
            timeout=45.0,
        )
    except Exception:
        return [], model, PROMPT_VERSION

    candidates: list[WebsiteCandidate] = []
    try:
        output = _parse_json(text)
        candidates.extend(output.candidates)
    except Exception:
        # Fallback: extract first https URL from free text
        for match in re.findall(r"https?://[^\s\"'<>]+", text):
            url = _normalize_candidate_url(match)
            if url and not _is_blocked_host(url):
                candidates.append(WebsiteCandidate(url=url, confidence=0.5))
                break

    seen_urls = {c.url for c in candidates}
    for url in _dedupe_urls(grounding_urls):
        if url not in seen_urls:
            candidates.append(WebsiteCandidate(url=url, confidence=0.4))
            seen_urls.add(url)

    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates[:5], model, PROMPT_VERSION
