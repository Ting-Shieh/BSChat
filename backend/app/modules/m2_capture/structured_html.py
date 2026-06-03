"""Vendor-neutral structured signals from HTML (JSON-LD, microdata, href)."""

import html
import json
import re
from typing import Any

_EMAIL_HREF_RE = re.compile(r'href=["\']mailto:([^"\']+)["\']', re.I)
_TEL_HREF_RE = re.compile(r'href=["\']tel:([^"\']+)["\']', re.I)
_JSON_LD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
_STRIP_TAGS_RE = re.compile(r"<[^>]+>")


def _normalize_phone(raw: str) -> str:
    value = raw.split(",")[0].strip()
    cleaned = re.sub(r"[^\d+]", "", value)
    return cleaned or raw.strip()


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _pick_image_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith("http"):
        return value
    if isinstance(value, dict):
        url = value.get("url") or value.get("@id")
        if isinstance(url, str) and url.startswith("http"):
            return url
    return None


def _org_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        name = value.get("name")
        return name.strip() if isinstance(name, str) and name.strip() else None
    return None


def _person_from_node(node: dict[str, Any]) -> dict | None:
    node_type = node.get("@type") or node.get("type")
    types = _as_list(node_type)
    type_names = {str(t).lower() for t in types}
    if "person" not in type_names and node_type != "Person":
        return None

    emails = []
    for e in _as_list(node.get("email")):
        if isinstance(e, str) and "@" in e:
            emails.append(e.lower())

    phones = []
    for p in _as_list(node.get("telephone")):
        if isinstance(p, str):
            phones.append(_normalize_phone(p))

    company = _org_name(node.get("worksFor")) or _org_name(node.get("affiliation"))
    image_url = _pick_image_url(node.get("image"))

    fields = {
        "name": (node.get("name") or "").strip() or None,
        "company": company,
        "title": (node.get("jobTitle") or "").strip() or None,
        "phones": phones[:3],
        "emails": emails[:3],
        "address": None,
        "website": None,
    }
    if not any([fields["name"], fields["company"], fields["phones"], fields["emails"]]):
        return None

    confidences = {k: 0.88 for k, v in fields.items() if v and k not in ("phones", "emails")}
    if fields["phones"]:
        confidences["phones"] = 0.88
    if fields["emails"]:
        confidences["emails"] = 0.88

    return {
        "fields": fields,
        "field_confidences": confidences,
        "image_url": image_url,
    }


def parse_json_ld_contact(html_text: str) -> dict | None:
    for block in _JSON_LD_RE.findall(html_text):
        try:
            payload = json.loads(html.unescape(block.strip()))
        except json.JSONDecodeError:
            continue

        nodes = _as_list(payload)
        if isinstance(payload, dict):
            if "@graph" in payload:
                nodes = _as_list(payload["@graph"])
            else:
                nodes = [payload]

        for node in nodes:
            if isinstance(node, dict):
                parsed = _person_from_node(node)
                if parsed:
                    parsed["resolver_type"] = "json_ld"
                    return parsed
    return None


def extract_href_contacts(html_text: str) -> tuple[list[str], list[str]]:
    emails = [e.lower().strip() for e in _EMAIL_HREF_RE.findall(html_text) if "@" in e]
    phones = [_normalize_phone(p) for p in _TEL_HREF_RE.findall(html_text)]
    emails = list(dict.fromkeys(emails))[:3]
    phones = list(dict.fromkeys(phones))[:3]
    return emails, phones


def extract_profile_image_url(html_text: str) -> str | None:
    for pattern in (
        r'<meta[^>]+itemprop=["\']image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    ):
        match = re.search(pattern, html_text, re.I)
        if match:
            url = html.unescape(match.group(1)).strip()
            if url.startswith("http") and "favicon" not in url.lower():
                return url
    return None


def html_to_visible_text(html_text: str, limit: int = 16000) -> str:
    cleaned = _TAG_RE.sub(" ", html_text)
    cleaned = _STRIP_TAGS_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit]
