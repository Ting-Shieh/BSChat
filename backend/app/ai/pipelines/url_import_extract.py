"""Gemini-first generic contact extraction from fetched HTML pages."""

import json
import re

from app.ai.gemini_client import gemini_generate_text
from app.core.config import get_settings
from app.modules.m2_capture.structured_html import (
    extract_href_contacts,
    extract_profile_image_url,
    html_to_visible_text,
)

settings = get_settings()

EXTRACT_PROMPT = """You extract ONE person's business contact from a fetched digital business card web page.

Page URL: {page_url}

Known mailto/tel hints from HTML (may be incomplete):
{href_hints}

Visible page text (truncated):
{visible_text}

Return JSON only:
{{
  "name": "display name — prefer Traditional Chinese when both zh/en exist",
  "company": "company or organization",
  "title": "job title / department if clearly part of role",
  "phones": ["E.164 or local phone strings"],
  "emails": ["emails"],
  "address": "postal address or null",
  "website": "company or card URL or null",
  "image_url": "absolute https URL of the person's card photo if clearly present, else null"
}}

Rules:
- Extract ONLY the card owner, not the platform brand (ignore SPIDERCARD, CamCard, etc. as name/company)
- name MUST be the person's display name; if the page shows both Chinese and English names, use Traditional Chinese (e.g. 賴昀君 not Aply Lai)
- title MUST be job title only (≤40 chars). NEVER put company marketing / About Us text in title
- company is employer name only, not platform name
- website is the person's employer official site if visible, NOT the digital-card platform URL (mysc.cc etc.)
- Do not invent fields; use null or empty arrays when absent
- image_url must be absolute https and look like a portrait/card image, not a favicon
"""


def _parse_extract_json(text: str) -> dict:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _build_result(parsed: dict, page_url: str, resolver_type: str) -> dict:
    fields = {
        "name": (parsed.get("name") or "").strip() or None,
        "company": (parsed.get("company") or "").strip() or None,
        "title": (parsed.get("title") or "").strip() or None,
        "phones": [str(p).strip() for p in (parsed.get("phones") or []) if str(p).strip()][:3],
        "emails": [str(e).strip().lower() for e in (parsed.get("emails") or []) if "@" in str(e)][:3],
        "address": (parsed.get("address") or "").strip() or None,
        "website": (parsed.get("website") or page_url or "").strip() or page_url,
    }
    confidences: dict[str, float] = {}
    for key in ("name", "company", "title", "address", "website"):
        if fields.get(key):
            confidences[key] = 0.9
    if fields["phones"]:
        confidences["phones"] = 0.9
    if fields["emails"]:
        confidences["emails"] = 0.9

    image_url = parsed.get("image_url")
    if isinstance(image_url, str) and not image_url.startswith("http"):
        image_url = None

    return {
        "fields": fields,
        "field_confidences": confidences,
        "raw_text": json.dumps(fields, ensure_ascii=False),
        "resolver_type": resolver_type,
        "image_url": image_url,
    }


async def extract_contact_from_html(html_text: str, page_url: str) -> dict:
    emails, phones = extract_href_contacts(html_text)
    href_hints = json.dumps({"emails": emails, "phones": phones}, ensure_ascii=False)
    visible = html_to_visible_text(html_text)

    prompt = EXTRACT_PROMPT.format(
        page_url=page_url,
        href_hints=href_hints,
        visible_text=visible,
    )
    text = await gemini_generate_text(prompt, model=settings.gemini_import_model, timeout=45.0)
    parsed = _parse_extract_json(text)

    if not parsed.get("image_url"):
        fallback_image = extract_profile_image_url(html_text)
        if fallback_image:
            parsed["image_url"] = fallback_image

    result = _build_result(parsed, page_url, "llm_html")
    if not any(
        [
            result["fields"]["name"],
            result["fields"]["company"],
            result["fields"]["phones"],
            result["fields"]["emails"],
        ]
    ):
        raise ValueError("EMPTY_LLM_EXTRACT")
    return result


def extract_contact_fallback(html_text: str, page_url: str) -> dict:
    """Offline fallback: href + visible text heuristics only (no vendor adapters)."""
    emails, phones = extract_href_contacts(html_text)
    image_url = extract_profile_image_url(html_text)
    visible = html_to_visible_text(html_text)

    name = None
    # First CJK token group that looks like a person name (2-4 chars) near start of visible text
    cjk_match = re.search(r"([\u4e00-\u9fff]{2,4})\s+([\u4e00-\u9fff]{2,4})?", visible)
    if cjk_match:
        name = cjk_match.group(0).strip()

    fields = {
        "name": name,
        "company": None,
        "title": None,
        "phones": phones,
        "emails": emails,
        "address": None,
        "website": page_url,
    }
    if not any([name, phones, emails]):
        raise ValueError("EMPTY_FALLBACK")

    confidences: dict[str, float] = {}
    if name:
        confidences["name"] = 0.5
    if phones:
        confidences["phones"] = 0.65
    if emails:
        confidences["emails"] = 0.65

    result = {
        "fields": fields,
        "field_confidences": confidences,
        "raw_text": visible[:4000],
        "resolver_type": "html_fallback",
    }
    if image_url:
        result["image_url"] = image_url
    return result
