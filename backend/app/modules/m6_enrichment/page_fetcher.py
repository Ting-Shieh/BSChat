import re
from urllib.parse import urljoin

import httpx

CANDIDATE_PATHS = ["", "/about", "/about-us", "/company", "/products", "/services", "/solution"]
MAX_CHARS = 12_000
TIMEOUT = 8.0


def _normalize_base_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url.rstrip("/")


async def fetch_pages(base_url: str) -> tuple[list[str], str]:
    base_url = _normalize_base_url(base_url)
    urls: list[str] = []
    combined: list[str] = []

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        headers={"User-Agent": "BSChatBot/1.0"},
        follow_redirects=True,
    ) as client:
        for path in CANDIDATE_PATHS:
            url = urljoin(base_url + "/", path.lstrip("/")) if path else base_url
            if url in urls:
                continue
            try:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    continue
                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    continue
                text = _strip_html(resp.text)
                if len(text) < 80:
                    continue
                urls.append(url)
                combined.append(f"--- {url} ---\n{text[:4000]}")
                if sum(len(c) for c in combined) >= MAX_CHARS:
                    break
            except Exception:
                continue

    body = "\n\n".join(combined)[:MAX_CHARS]
    return urls, body


def _strip_html(html: str) -> str:
    text = html
    for tag in ("script", "style", "noscript"):
        text = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
