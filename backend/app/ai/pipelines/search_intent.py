"""Search intent parsing — Gemini first; intent_kind via LLM (DDR-v4-17)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.ai.gemini_client import gemini_generate_text
from app.ai.openai_client import openai_generate_text
from app.ai.schemas.search_rerank import ParsedIntent
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
INTENT_PROMPT_VERSION = "v4"

IntentKind = Literal["find_people", "browse_public", "browse_public_more"]

INTENT_PROMPT = """You parse a B2B contact-search utterance for BSChat (private rolodex + optional public recommend pool).

{prior_block}Current user message: {query}

Return JSON only:
{{
  "intent_kind": "find_people" | "browse_public" | "browse_public_more",
  "products": ["industry or product themes"],
  "roles": ["job functions, soft preference"],
  "events": ["event or occasion labels if mentioned"],
  "regions": ["regions if mentioned"],
  "keywords": ["2-8 retrieval terms — short phrases likely to appear on cards or company data"],
  "semantic_query": "one sentence describing who/what the user is looking for, for semantic search",
  "hard_roles": [],
  "hard_companies": [],
  "hard_products": []
}}

intent_kind rules (judge CURRENT message; use prior turns only as context):
- browse_public: user wants an overview / who is in the public recommend pool, WITHOUT a specific product, role, or company filter yet.
  IMPORTANT: Questions like 「公開商務有誰」「公開池有誰」「有哪些公開身份」「誰公開了」are ALWAYS browse_public — never find_people.
  Examples: 公開商務有誰、公開池有哪些人、有誰公開、列出公開身份、公開推薦有誰、公開的人有哪些
- browse_public_more: after a browse, user asks to show more from the pool (列更多、再多幾個、展開更多公開、列更多公開身份)
- find_people: user is looking for people matching products / roles / companies / situations (including follow-ups that narrow a previous browse, e.g. 只要威剛、誰做工業電腦)

Guidelines for retrieval fields:
- Use Traditional Chinese when the query is Chinese
- Decompose natural language into multiple keywords; never return the whole sentence as one keyword
- hard_* arrays ONLY when the user explicitly requires ALL results to satisfy them (e.g. 就好, 只要, 仅限, 從…人脈中找…)
- Put literal searchable phrases into hard_* (job titles, company names, product names) as they might appear on cards
- When not an explicit hard constraint, use keywords / roles / products instead
- Do not invent a stored user profile; extract only from this query (+ prior if needed for hard filters)
- For browse_public / browse_public_more, products/roles/keywords may be empty
- semantic_query should capture implied meaning in one concise sentence (empty string OK for pure browse)
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
    """Offline keyword fallback — find_people only (no invent browse)."""
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


def _offline_meta_intent(query: str, prior_turns: list[str] | None) -> ParsedIntent | None:
    """Last-resort meta classifier when LLM is down — only directory browse acts.

    Not a product/role keyword list; detects «ask about the public pool itself».
    """
    q = (query or "").strip().lower()
    if not q:
        return None
    more_hints = ("列更多", "再多", "展開更多", "更多公開", "再給我幾個")
    if any(h in q for h in more_hints) and (
        "公開" in q or (prior_turns and any("公開" in (t or "") for t in prior_turns[-2:]))
    ):
        return ParsedIntent(intent_kind="browse_public_more")

    # Asking who/what is in the public recommend pool (no specific product filter).
    pool_markers = ("公開商務", "公開池", "公開身份", "公開推薦", "公開名片", "公開的人")
    ask_markers = ("有誰", "有哪些", "名單", "列表", "列出", "誰公開", "有沒有人")
    if any(m in q for m in pool_markers) and (
        any(a in q for a in ask_markers) or q.endswith("誰") or "誰" in q
    ):
        return ParsedIntent(intent_kind="browse_public")
    if q in ("公開商務有誰", "公開商務有誰?", "公開商務有誰？"):
        return ParsedIntent(intent_kind="browse_public")
    return None


async def _parse_intent_llm(query: str, prior_turns: list[str] | None) -> ParsedIntent:
    if prior_turns:
        lines = "\n".join(f"- {t}" for t in prior_turns[-4:])
        prior_block = f"Prior turns in this search thread:\n{lines}\n\n"
    else:
        prior_block = ""
    prompt = INTENT_PROMPT.format(query=query, prior_block=prior_block)
    provider = settings.effective_search_provider
    if provider == "openai":
        text = await openai_generate_text(
            prompt, model=settings.openai_search_model, timeout=30.0
        )
    elif provider == "claude" and settings.anthropic_api_key:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.search_rerank_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text
    else:
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
            offline = _offline_meta_intent(query, prior_turns)
            if offline is not None:
                return IntentParseResult(intent=offline, llm_ok=False, llm_error=err)
            return IntentParseResult(
                intent=_parse_intent_fallback(query),
                llm_ok=False,
                llm_error=err,
            )

    offline = _offline_meta_intent(query, prior_turns)
    if offline is not None:
        return IntentParseResult(
            intent=offline, llm_ok=False, llm_error="SEARCH_LLM_DISABLED"
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
