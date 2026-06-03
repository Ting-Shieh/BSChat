import re
from urllib.parse import urlparse

import httpx

from app.ai.pipelines.website_discovery import infer_company_website_candidates

MAX_PROBE = 8
TIMEOUT = 5.0

_SUFFIX_STOPWORDS = frozenset(
    {"co", "ltd", "inc", "corp", "llc", "company", "group", "holdings", "technology", "tech", "limited"}
)

_GENERIC_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "live.com",
        "icloud.com",
        "me.com",
        "msn.com",
        "ymail.com",
        "proton.me",
        "protonmail.com",
    }
)


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return bool(parsed.netloc)
    except Exception:
        return False


def _normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url.rstrip("/")


def _website_from_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[-1].lower().strip()
    if not domain or domain in _GENERIC_EMAIL_DOMAINS or "." not in domain:
        return None
    return f"https://www.{domain}"


def _ascii_tokens(text: str) -> list[str]:
    return [p.lower() for p in re.findall(r"[a-zA-Z0-9]+", text) if len(p) >= 2]


def _slug_candidates(company_name: str) -> list[str]:
    names = [company_name]
    names.extend(re.findall(r"[（(]([^）)]+)[）)]", company_name))

    slugs: list[str] = []
    seen: set[str] = set()

    def add_slug(slug: str) -> None:
        slug = slug.strip("-")
        if slug and slug not in seen:
            seen.add(slug)
            slugs.append(slug)

    for name in names:
        tokens = _ascii_tokens(name)
        meaningful = [t for t in tokens if t not in _SUFFIX_STOPWORDS]
        if meaningful:
            add_slug(meaningful[0])
            if len(meaningful) > 1:
                add_slug("-".join(meaningful[:3]))

    if slugs:
        return slugs

    cjk = re.sub(r"[^\u4e00-\u9fff]", "", company_name)
    if len(cjk) >= 2:
        return [cjk[:4]]
    return []


def _heuristic_domain_candidates(company_name: str) -> list[str]:
    candidates: list[str] = []
    for slug in _slug_candidates(company_name):
        candidates.extend(
            [
                f"https://www.{slug}.com.tw",
                f"https://{slug}.com.tw",
                f"https://www.{slug}.com",
                f"https://{slug}.com",
            ]
        )
    return candidates


async def _probe_url(client: httpx.AsyncClient, url: str) -> bool:
    try:
        resp = await client.head(url, follow_redirects=True)
        if resp.status_code < 400:
            return True
        resp = await client.get(url, follow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False


async def _probe_first_reachable(urls: list[str]) -> str | None:
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": "BSChatBot/1.0"}) as client:
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            if await _probe_url(client, url):
                return url
            if len(seen) >= MAX_PROBE:
                break
    return None


async def discover_website(
    company_name: str,
    contact_website: str | None = None,
    contact_email: str | None = None,
) -> str | None:
    if contact_website and _is_valid_url(contact_website):
        return _normalize_url(contact_website)

    email_site = _website_from_email(contact_email)
    if email_site:
        found = await _probe_first_reachable([email_site])
        if found:
            return found

    ai_candidates, _, _ = await infer_company_website_candidates(
        company_name,
        contact_email=contact_email,
    )
    if ai_candidates:
        found = await _probe_first_reachable([c.url for c in ai_candidates])
        if found:
            return found

    return await _probe_first_reachable(_heuristic_domain_candidates(company_name))
