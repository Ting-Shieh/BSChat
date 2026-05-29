import json
import re
import uuid

from app.ai.gemini_client import gemini_generate_text
from app.ai.schemas.search_rerank import MatchSource, ParsedIntent, RerankItem, SearchRerankResponse
from app.core.config import get_settings
from app.modules.m5_search.constraints import MIN_MATCH_SCORE, filter_rerank_results, has_hard_constraints
from app.modules.m5_search.retrieval import CandidateDoc

settings = get_settings()
PROMPT_VERSION = "v3"

RERANK_PROMPT = """You are a B2B contact search assistant. Rank contacts from the user's private rolodex.

User query: {query}

Hard constraints (every returned contact MUST satisfy ALL — otherwise exclude):
{hard_constraints}

Candidates JSON:
{candidates}

Return JSON only:
{{
  "results": [
    {{
      "contact_id": "uuid-from-candidates",
      "match_score": 0.0-1.0,
      "match_reason": "≤200 chars Traditional Chinese",
      "match_sources": [
        {{ "field": "company_products|responsibility_scope|title|company_name|source_label", "value": "...", "confidence": 0.0-1.0 }}
      ]
    }}
  ]
}}

Guidelines:
- Use only contact_id values from the candidates list
- Interpret semantic intent (synonyms, industry language, implied roles) — do not require literal keyword overlap
- If hard constraints are listed, exclude anyone who fails them; return fewer or zero results rather than partial matches
- match_sources must cite real candidate fields
- Use Traditional Chinese for match_reason
- Never return a contact whose match_reason admits they fail a hard constraint
"""


def _intent_terms(intent: ParsedIntent) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for raw in (
        intent.keywords
        + intent.products
        + intent.roles
        + intent.events
        + intent.hard_roles
        + intent.hard_companies
        + intent.hard_products
    ):
        token = raw.strip().lower()
        if len(token) >= 2 and token not in seen:
            seen.add(token)
            terms.append(token)
    return terms


def _mock_rerank(query: str, candidates: list[dict], intent: ParsedIntent) -> SearchRerankResponse:
    """Offline fallback only — uses intent terms, no domain dictionaries."""
    terms = _intent_terms(intent) or [query.strip().lower()[:32]]
    scored: list[RerankItem] = []
    candidate_map = {c["contact_id"]: c for c in candidates}

    doc_map = {
        cid: CandidateDoc(
            contact_id=uuid.UUID(cid),
            display_name=raw.get("display_name"),
            company_name=raw.get("company_name"),
            title=raw.get("title"),
            responsibility_scope=raw.get("responsibility_scope"),
            responsibility_confidence=raw.get("responsibility_confidence"),
            source_label=raw.get("source_label"),
            review_status=raw.get("review_status", "pending_review"),
            phones=[],
            emails=[],
            image_url=raw.get("image_url"),
            company_products=raw.get("company_products") or [],
            products_confidence=raw.get("products_confidence"),
            search_text=raw.get("search_text", ""),
            retrieval_score=float(raw.get("retrieval_score") or 0),
        )
        for cid, raw in candidate_map.items()
    }

    from app.modules.m5_search.constraints import satisfies_hard_constraints

    for c in candidates:
        cid = c["contact_id"]
        cand = doc_map[cid]
        text = (c.get("search_text") or "").lower()
        title = (c.get("title") or "").lower()
        hits = sum(1 for t in terms if t in text or t in title)
        score = max(0.2 + min(hits * 0.15, 0.5), float(c.get("retrieval_score") or 0) + 0.1)

        if has_hard_constraints(intent):
            if not satisfies_hard_constraints(cand, intent):
                continue
            score = max(score, MIN_MATCH_SCORE + 0.05)
        elif hits == 0:
            continue

        sources: list[MatchSource] = []
        if c.get("title"):
            sources.append(MatchSource(field="title", value=c["title"]))

        if score >= MIN_MATCH_SCORE:
            scored.append(
                RerankItem(
                    contact_id=cid,
                    match_score=min(score, 0.95),
                    match_reason=f"與「{query}」相關：{c.get('display_name')} · {c.get('company_name') or ''}",
                    match_sources=sources,
                )
            )

    scored.sort(key=lambda x: x.match_score, reverse=True)
    if has_hard_constraints(intent):
        scored = filter_rerank_results(scored, doc_map, intent)

    return SearchRerankResponse(results=scored[: settings.search_result_limit])


def _parse_json(text: str) -> SearchRerankResponse:
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    parsed = json.loads(text.strip())
    return SearchRerankResponse.model_validate(parsed)


def _hard_constraints_summary(intent: ParsedIntent) -> str:
    if not has_hard_constraints(intent):
        return "（無）"
    payload = {
        "hard_roles": intent.hard_roles,
        "hard_companies": intent.hard_companies,
        "hard_products": intent.hard_products,
    }
    return json.dumps(payload, ensure_ascii=False)


async def rerank_contacts(
    query: str,
    candidates: list[dict],
    intent: ParsedIntent,
) -> tuple[SearchRerankResponse, bool]:
    if not candidates:
        return SearchRerankResponse(), False

    if not settings.search_will_use_llm:
        return _mock_rerank(query, candidates, intent), False

    prompt = RERANK_PROMPT.format(
        query=query,
        hard_constraints=_hard_constraints_summary(intent),
        candidates=json.dumps(candidates, ensure_ascii=False)[:12000],
    )

    try:
        if settings.gemini_api_key:
            text = await gemini_generate_text(prompt, model=settings.gemini_search_model)
            return _parse_json(text), False

        if settings.anthropic_api_key:
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            msg = await client.messages.create(
                model=settings.search_rerank_model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            return _parse_json(msg.content[0].text), False
    except Exception:
        return _mock_rerank(query, candidates, intent), True

    return _mock_rerank(query, candidates, intent), False
