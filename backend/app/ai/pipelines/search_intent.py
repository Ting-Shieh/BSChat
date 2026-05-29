"""Search intent parsing — Gemini first, minimal fallback."""

import json
import re

from app.ai.gemini_client import gemini_generate_text
from app.ai.schemas.search_rerank import ParsedIntent
from app.core.config import get_settings

settings = get_settings()
INTENT_PROMPT_VERSION = "v2"

INTENT_PROMPT = """You parse a B2B contact search query into structured retrieval intent for a private business-card rolodex.

User query: {query}

Return JSON only:
{{
  "products": ["industry or product themes"],
  "roles": ["job functions, soft preference"],
  "events": ["event or occasion labels if mentioned"],
  "regions": ["regions if mentioned"],
  "keywords": ["2-8 retrieval terms — short phrases likely to appear on cards or company data"],
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}}

Guidelines:
- Use Traditional Chinese when the query is Chinese
- Decompose natural language into multiple keywords; never return the whole sentence as one keyword
- hard_* arrays ONLY when the user explicitly requires ALL results to satisfy them (e.g. 就好, 只要, 仅限, 從…人脈中找…)
- Put literal searchable phrases into hard_* (job titles, company names, product names) as they might appear on cards — do not use internal codes the user did not imply
- When not an explicit hard constraint, use keywords / roles / products instead
- Do not invent a stored user profile; extract only from this query
- Use empty arrays when a field does not apply
"""


def _parse_intent_json(text: str) -> ParsedIntent:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text.strip())
    return ParsedIntent.model_validate(parsed)


def _parse_intent_fallback(query: str) -> ParsedIntent:
    """Minimal offline fallback — no domain keyword lists."""
    keywords = [w for w in re.split(r"[\s，,、？?！!。]+", query.strip()) if len(w) >= 2]
    if len(keywords) == 1 and len(keywords[0]) > 4:
        text = keywords[0]
        for i in range(len(text) - 1):
            piece = text[i : i + 2]
            if piece not in keywords:
                keywords.append(piece)
    if not keywords and query.strip():
        keywords = [query.strip()[:32]]
    return ParsedIntent(keywords=keywords[:8])


async def _parse_intent_gemini(query: str) -> ParsedIntent:
    prompt = INTENT_PROMPT.format(query=query)
    text = await gemini_generate_text(prompt, model=settings.gemini_search_model, timeout=30.0)
    intent = _parse_intent_json(text)
    if not intent.keywords and not intent.products and not intent.roles:
        intent.keywords = _parse_intent_fallback(query).keywords
    return intent


async def parse_intent(query: str) -> ParsedIntent:
    if settings.search_skip_intent_parse:
        return ParsedIntent(keywords=[query.strip()])

    if settings.search_will_use_llm and settings.gemini_api_key:
        try:
            return await _parse_intent_gemini(query)
        except Exception:
            pass

    return _parse_intent_fallback(query)
