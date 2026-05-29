import re
from urllib.parse import urlparse

import httpx

MAX_PROBE = 3
TIMEOUT = 5.0


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


def _slug_candidates(company_name: str) -> list[str]:
    ascii_parts = re.findall(r"[a-zA-Z0-9]+", company_name)
    if ascii_parts:
        slug = "-".join(p.lower() for p in ascii_parts[:4])
        return [slug]
    # CJK: use first few chars as heuristic (limited)
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", company_name)
    if len(cjk) >= 2:
        short = cjk[:4]
        return [short]
    return []


async def _probe_url(client: httpx.AsyncClient, url: str) -> bool:
    try:
        resp = await client.head(url, follow_redirects=True)
        if resp.status_code < 400:
            return True
        resp = await client.get(url, follow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False


async def discover_website(company_name: str, contact_website: str | None = None) -> str | None:
    if contact_website and _is_valid_url(contact_website):
        return _normalize_url(contact_website)

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

    # Known hints for common Taiwan company patterns
    lower = company_name.lower()
    if "amazon" in lower or "亞馬遜" in company_name:
        candidates.insert(0, "https://aws.amazon.com")
    if "google" in lower or "谷歌" in company_name:
        candidates.insert(0, "https://about.google")

    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": "BSChatBot/1.0"}) as client:
        for url in candidates:
            if url in seen:
                continue
            seen.add(url)
            if await _probe_url(client, url):
                return url
            if len(seen) >= MAX_PROBE:
                break
    return None
