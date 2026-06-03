"""Post-process imported contact fields (vendor-neutral)."""

import html
import re

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_NAME_LIKE_RE = re.compile(r"^[\u4e00-\u9fff]{2,4}$")
_TITLE_LIKE_RE = re.compile(
    r"^[\u4e00-\u9fffA-Za-z0-9\s·\-/]{2,40}$"
)
_MARKETING_MARKERS = (
    "manufacturer",
    "largest",
    "ranking",
    "product lines",
    "committed to",
    "main product",
    "global brands",
    "電子科技業",
)
_PLATFORM_HOSTS = ("mysc.cc", "spidercard.com", "camcard.com", "hihello.com")


def _unescape(value: str | None) -> str | None:
    if not value:
        return None
    text = html.unescape(value).strip()
    return text or None


def _has_cjk(text: str | None) -> bool:
    return bool(text and _CJK_RE.search(text))


def _is_marketing(text: str | None) -> bool:
    if not text:
        return False
    lower = text.lower()
    if len(text) > 80:
        return True
    return any(marker in lower for marker in _MARKETING_MARKERS)


_NOISE_CJK_NAMES = frozenset(
    {"繁體中文", "简体中文", "請選擇", "複製成功", "複製連結", "聯絡資訊", "公司資訊"}
)
_BILINGUAL_NAME_RE = re.compile(
    r"([\u4e00-\u9fff]{2,4})\s+[A-Za-z][A-Za-z\s'.-]{0,40}"
)


def _guess_cjk_name(visible_text: str) -> str | None:
    head = visible_text[:3000]
    for match in _BILINGUAL_NAME_RE.finditer(head):
        candidate = match.group(1)
        if candidate not in _NOISE_CJK_NAMES:
            return candidate
    for match in _NAME_LIKE_RE.finditer(head):
        candidate = match.group(0)
        if candidate not in _NOISE_CJK_NAMES:
            return candidate
    return None


def _guess_cjk_titles(visible_text: str) -> list[str]:
    chunk = visible_text[:3000]
    titles: list[str] = []
    for line in re.split(r"\s{2,}|\n", chunk):
        line = line.strip()
        if not line or len(line) > 30:
            continue
        if not _CJK_RE.search(line):
            continue
        if _is_marketing(line):
            continue
        if any(w in line for w in ("請選擇", "複製", "Download", "Contact info", "Company info")):
            continue
        if _TITLE_LIKE_RE.match(line) and line not in titles:
            titles.append(line)
        if len(titles) >= 2:
            break
    return titles


def _pick_company(fields: dict, visible_text: str) -> str | None:
    company = fields.get("company")
    if company and _has_cjk(company):
        # Drop trailing English duplicate on same field
        parts = re.split(r"\s{2,}|\n", company)
        cjk_parts = [p.strip() for p in parts if _has_cjk(p.strip())]
        if cjk_parts:
            return cjk_parts[0]
    if company and not _has_cjk(company):
        for line in re.split(r"\s{2,}|\n", visible_text):
            line = line.strip()
            if _has_cjk(line) and any(s in line for s in ("公司", "股份", "有限", "科技", "Inc", "Ltd")):
                if len(line) <= 40:
                    return line
    return company


def _pick_website(website: str | None, page_url: str) -> str | None:
    if not website:
        return None
    host = website.lower()
    if any(p in host for p in _PLATFORM_HOSTS):
        return None
    if website.rstrip("/") == page_url.rstrip("/"):
        return None
    return website


def normalize_import_fields(fields: dict, *, html_text: str = "", page_url: str = "") -> dict:
    """Clean LLM / fallback output before persisting."""
    from app.modules.m2_capture.structured_html import html_to_visible_text

    visible = html_to_visible_text(html_text) if html_text else ""

    name = _unescape(fields.get("name"))
    company = _unescape(fields.get("company"))
    title = _unescape(fields.get("title"))
    address = _unescape(fields.get("address"))
    website = _unescape(fields.get("website"))

    if visible:
        cjk_name = _guess_cjk_name(visible)
        name_is_latin_only = name and not _has_cjk(name)
        name_matches_company = (
            bool(name and company and name.strip().lower() == company.strip().lower())
        )
        if cjk_name and (not name or name_is_latin_only or name_matches_company):
            name = cjk_name

    if _is_marketing(title):
        title = None

    if visible and (not title or _is_marketing(title)):
        guessed = _guess_cjk_titles(visible)
        if guessed:
            title = " · ".join(guessed[:2])

    if visible and company:
        company = _pick_company({"company": company}, visible)

    website = _pick_website(website, page_url)

    phones = [_unescape(str(p)) or str(p) for p in (fields.get("phones") or [])]
    phones = [re.sub(r"\s+#", " ext ", p).strip() for p in phones if p]

    emails = [(_unescape(str(e)) or str(e)).lower() for e in (fields.get("emails") or []) if e]

    return {
        "name": name,
        "company": company,
        "title": title,
        "phones": phones[:3],
        "emails": emails[:3],
        "address": address,
        "website": website or None,
    }
