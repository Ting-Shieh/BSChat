"""Search intent parsing — OpenAI Chat Completions (system / user).

Each turn is classified from the CURRENT user message only.
Prior turns must NOT be stuffed into the user role (that caused browse carry-over).
Session history is used elsewhere for retrieval (`effective_query`), not for intent_kind.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.ai.gemini_client import gemini_generate_text
from app.ai.openai_client import openai_chat
from app.ai.schemas.search_rerank import ParsedIntent
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
INTENT_PROMPT_VERSION = "v8"

IntentKind = Literal["find_people", "browse_public", "browse_public_more"]

# System role = stable policy. Live query goes only in the user message.
INTENT_SYSTEM = """You are BSChat's search-intent classifier for a B2B contact product
(private rolodex + optional public recommend pool).

Classify this one user message in isolation. Return JSON only (no markdown fences):
{
  "intent_kind": "find_people" | "browse_public" | "browse_public_more",
  "products": ["industry or product themes"],
  "roles": ["job titles / functions"],
  "events": ["event or occasion labels if mentioned"],
  "regions": ["regions if mentioned"],
  "keywords": ["2-8 retrieval terms — short phrases likely to appear on cards or company data"],
  "semantic_query": "one sentence describing who/what the user is looking for",
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}

intent_kind:
1) find_people — looking for people by any filter (default when unsure).
   Job title/role, industry, product, company, region, or 「有…嗎／誰是／找…」with a concrete attribute.
   Examples: 有ＰＭ嗎、有業務嗎、有雲端相關業者嗎、誰做工業電腦、只要威剛的、找做 IoT 的

2) browse_public — unfiltered overview of the public recommend pool (no filter in the message).
   Examples: 公開商務有誰、公開池有誰、現在你可以推薦誰、有哪些公開身份、誰公開了

3) browse_public_more — only asking to expand the same unfiltered pool preview.
   Examples: 列更多、再多幾個、展開更多、列更多公開身份
   If the message also adds a filter (role/product/…) → find_people.

Field guidelines:
- Use Traditional Chinese when the query is Chinese
- Decompose into multiple keywords; never return the whole sentence as one keyword
- Role asks: put title in roles AND keywords (e.g. roles:["PM","產品經理"], keywords:["PM","產品經理"])
- hard_* only when the user explicitly requires ALL results to satisfy them (只要、就好、仅限…)
- For browse_* , products/roles/keywords may be empty; semantic_query may be ""
"""


@dataclass
class IntentParseResult:
    intent: ParsedIntent
    llm_ok: bool
    llm_error: str | None = None


def _parse_intent_json(text: str) -> ParsedIntent:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text.strip())
    kind = parsed.get("intent_kind") or "find_people"
    if kind not in ("find_people", "browse_public", "browse_public_more"):
        parsed["intent_kind"] = "find_people"
    return ParsedIntent.model_validate(parsed)


def _parse_intent_fallback(query: str) -> ParsedIntent:
    """Mechanical retrieval fallback when LLM is unavailable — always find_people.

    Does NOT invent browse_public. Splits the utterance into rough keywords only.
    """
    keywords = [w for w in re.split(r"[\s，,、？?！!。]+", query.strip()) if len(w) >= 2]
    if len(keywords) == 1 and len(keywords[0]) > 4:
        text = keywords[0]
        for i in range(len(text) - 1):
            piece = text[i : i + 2]
            if piece not in keywords:
                keywords.append(piece)
    if not keywords and query.strip():
        keywords = [query.strip()[:32]]
    return ParsedIntent(intent_kind="find_people", keywords=keywords[:8])


def _ensure_keywords(intent: ParsedIntent, query: str) -> ParsedIntent:
    if (
        intent.intent_kind == "find_people"
        and not intent.keywords
        and not intent.products
        and not intent.roles
        and not intent.hard_companies
        and not intent.hard_roles
        and not intent.hard_products
    ):
        intent.keywords = _parse_intent_fallback(query).keywords
    return intent


async def _parse_intent_openai(query: str) -> ParsedIntent:
    # OpenAI standard: system = policy, user = this turn only.
    text = await openai_chat(
        [
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": query},
        ],
        model=settings.openai_search_model,
        timeout=30.0,
        response_format={"type": "json_object"},
    )
    return _ensure_keywords(_parse_intent_json(text), query)


async def _parse_intent_gemini(query: str) -> ParsedIntent:
    """Gemini path: same policy text, single prompt (no native roles). Prefer OpenAI."""
    prompt = INTENT_SYSTEM + "\n\nUser message:\n" + query + "\n\nReturn JSON only."
    text = await gemini_generate_text(
        prompt, model=settings.gemini_search_model, timeout=30.0
    )
    return _ensure_keywords(_parse_intent_json(text), query)


async def _parse_intent_claude(query: str) -> ParsedIntent:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    msg = await client.messages.create(
        model=settings.search_rerank_model,
        max_tokens=1024,
        system=INTENT_SYSTEM,
        messages=[{"role": "user", "content": query}],
    )
    return _ensure_keywords(_parse_intent_json(msg.content[0].text), query)


async def _parse_intent_llm(query: str) -> ParsedIntent:
    provider = settings.effective_search_provider
    if provider == "openai":
        return await _parse_intent_openai(query)
    if provider == "claude" and settings.anthropic_api_key:
        return await _parse_intent_claude(query)
    return await _parse_intent_gemini(query)


async def parse_intent_result(
    query: str,
    *,
    prior_turns: list[str] | None = None,
) -> IntentParseResult:
    # prior_turns ignored for intent — kept as unused kwarg for call-site compatibility.
    # Multiturn context belongs in retrieval (effective_query), not in intent classification.
    _ = prior_turns

    if settings.search_skip_intent_parse:
        return IntentParseResult(
            intent=ParsedIntent(intent_kind="find_people", keywords=[query.strip()]),
            llm_ok=False,
            llm_error="SEARCH_SKIP_INTENT_PARSE",
        )

    if settings.search_will_use_llm:
        try:
            intent = await _parse_intent_llm(query)
            return IntentParseResult(intent=intent, llm_ok=True)
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            logger.warning("search intent LLM failed: %s", err[:300])
            return IntentParseResult(
                intent=_parse_intent_fallback(query),
                llm_ok=False,
                llm_error=err,
            )

    return IntentParseResult(
        intent=_parse_intent_fallback(query),
        llm_ok=False,
        llm_error="SEARCH_LLM_DISABLED",
    )


async def parse_intent(
    query: str,
    *,
    prior_turns: list[str] | None = None,
) -> ParsedIntent:
    """Back-compat wrapper — prefer parse_intent_result in new code."""
    return (await parse_intent_result(query, prior_turns=prior_turns)).intent
