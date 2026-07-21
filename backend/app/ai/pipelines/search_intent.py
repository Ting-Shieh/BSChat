"""Search intent parsing — OpenAI Chat Completions (system / user); LLM owns intent_kind.

DDR-v4-17: multi-turn browse vs find_people is semantic judgment, not keyword rules.
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
INTENT_PROMPT_VERSION = "v6"

IntentKind = Literal["find_people", "browse_public", "browse_public_more"]

# System role = stable policy. Do not put the live query here.
INTENT_SYSTEM = """You are BSChat's search-intent classifier for a B2B contact product
(private rolodex + optional public recommend pool).

Return JSON only (no markdown fences) with this shape:
{
  "intent_kind": "find_people" | "browse_public" | "browse_public_more",
  "products": ["industry or product themes"],
  "roles": ["job functions, soft preference"],
  "events": ["event or occasion labels if mentioned"],
  "regions": ["regions if mentioned"],
  "keywords": ["2-8 retrieval terms — short phrases likely to appear on cards or company data"],
  "semantic_query": "one sentence describing who/what the user is looking for",
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}

intent_kind (judge the CURRENT user message; prior turns are context only — never copy prior intent_kind):
- browse_public: current message asks who/what is in the public recommend pool itself,
  with NO product, industry, role, or company filter yet.
  Examples: 公開商務有誰、公開池有誰、有哪些公開身份、誰公開了、列出公開身份
- browse_public_more: current message only asks to show more from that pool preview
  (列更多、再多幾個、展開更多公開).
- find_people: current message looks for people by theme/filter — including follow-ups that
  narrow a previous browse (有雲端相關業者嗎、誰做工業電腦、只要威剛的、找做 IoT 的).
  If the user names an industry, product, company, role, or 「相關業者／廠商／供應商」, use find_people.

Field guidelines:
- Use Traditional Chinese when the query is Chinese
- Decompose into multiple keywords; never return the whole sentence as one keyword
- hard_* only when the user explicitly requires ALL results to satisfy them (只要、就好、仅限…)
- For browse_public / browse_public_more, products/roles/keywords may be empty
- For find_people after a browse, fill keywords/products from the CURRENT filter
- semantic_query: one concise sentence (empty string OK for pure browse)
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


def _user_message(query: str, prior_turns: list[str] | None) -> str:
    parts: list[str] = []
    if prior_turns:
        lines = "\n".join(f"- {t}" for t in prior_turns[-4:])
        parts.append(f"Prior turns in this search thread:\n{lines}")
    parts.append(f"Current user message:\n{query}")
    return "\n\n".join(parts)


async def _parse_intent_openai(query: str, prior_turns: list[str] | None) -> ParsedIntent:
    text = await openai_chat(
        [
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": _user_message(query, prior_turns)},
        ],
        model=settings.openai_search_model,
        timeout=30.0,
        response_format={"type": "json_object"},
    )
    intent = _parse_intent_json(text)
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


async def _parse_intent_gemini(query: str, prior_turns: list[str] | None) -> ParsedIntent:
    """Gemini path: same policy text, single prompt (no native roles). Prefer OpenAI."""
    prompt = (
        INTENT_SYSTEM
        + "\n\n---\n\n"
        + _user_message(query, prior_turns)
        + "\n\nReturn JSON only."
    )
    text = await gemini_generate_text(
        prompt, model=settings.gemini_search_model, timeout=30.0
    )
    intent = _parse_intent_json(text)
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


async def _parse_intent_claude(query: str, prior_turns: list[str] | None) -> ParsedIntent:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    msg = await client.messages.create(
        model=settings.search_rerank_model,
        max_tokens=1024,
        system=INTENT_SYSTEM,
        messages=[{"role": "user", "content": _user_message(query, prior_turns)}],
    )
    intent = _parse_intent_json(msg.content[0].text)
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


async def _parse_intent_llm(query: str, prior_turns: list[str] | None) -> ParsedIntent:
    provider = settings.effective_search_provider
    if provider == "openai":
        return await _parse_intent_openai(query, prior_turns)
    if provider == "claude" and settings.anthropic_api_key:
        return await _parse_intent_claude(query, prior_turns)
    return await _parse_intent_gemini(query, prior_turns)


async def parse_intent_result(
    query: str,
    *,
    prior_turns: list[str] | None = None,
) -> IntentParseResult:
    if settings.search_skip_intent_parse:
        return IntentParseResult(
            intent=ParsedIntent(intent_kind="find_people", keywords=[query.strip()]),
            llm_ok=False,
            llm_error="SEARCH_SKIP_INTENT_PARSE",
        )

    if settings.search_will_use_llm:
        try:
            intent = await _parse_intent_llm(query, prior_turns)
            return IntentParseResult(intent=intent, llm_ok=True)
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            logger.warning("search intent LLM failed: %s", err[:300])
            # No keyword invent of browse_* — degrade to mechanical find_people only.
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
