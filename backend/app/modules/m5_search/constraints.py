"""DDR-73: hard constraint matching — dynamic terms from LLM intent, no fixed alias tables."""

import re

from app.ai.schemas.search_rerank import ParsedIntent, RerankItem
from app.modules.m5_search.retrieval import CandidateDoc

NEGATIVE_REASON_PATTERNS = re.compile(
    r"並非|并非|不是|不符合|不符|並不|并不|除外|排除|不符合條件"
)


def has_hard_constraints(intent: ParsedIntent) -> bool:
    return bool(intent.hard_roles or intent.hard_companies or intent.hard_products)


def _contact_blob(candidate: CandidateDoc) -> str:
    products = " ".join(str(p) for p in (candidate.company_products or []))
    parts = [
        candidate.display_name,
        candidate.company_name,
        candidate.title,
        candidate.responsibility_scope,
        candidate.source_label,
        products,
        candidate.search_text,
    ]
    return " ".join(p for p in parts if p).lower()


def _constraint_tokens(constraint: str) -> list[str]:
    return [
        t.lower()
        for t in re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9]{2,}", constraint)
    ]


def constraint_matches(blob: str, constraint: str) -> bool:
    """Match using LLM-provided constraint text only (substring or token overlap)."""
    value = constraint.strip()
    if not value:
        return True
    lower = value.lower()
    if lower in blob:
        return True
    tokens = _constraint_tokens(value)
    if not tokens:
        return lower in blob
    return any(token in blob for token in tokens)


def satisfies_hard_constraints(candidate: CandidateDoc, intent: ParsedIntent) -> bool:
    if not has_hard_constraints(intent):
        return True

    blob = _contact_blob(candidate)

    for company in intent.hard_companies:
        if not constraint_matches(blob, company):
            return False

    for role in intent.hard_roles:
        if not constraint_matches(blob, role):
            return False

    for product in intent.hard_products:
        if not constraint_matches(blob, product):
            return False

    return True


def match_reason_contradicts_hard(item: RerankItem, intent: ParsedIntent) -> bool:
    if not has_hard_constraints(intent):
        return False
    return bool(NEGATIVE_REASON_PATTERNS.search(item.match_reason))


def filter_rerank_results(
    items: list[RerankItem],
    candidate_map: dict[str, CandidateDoc],
    intent: ParsedIntent,
) -> list[RerankItem]:
    """Boundary filter only — no match_score threshold (DDR-101)."""
    kept: list[RerankItem] = []
    for item in items:
        cand = candidate_map.get(item.contact_id)
        if not cand:
            continue
        if not satisfies_hard_constraints(cand, intent):
            continue
        if match_reason_contradicts_hard(item, intent):
            continue
        kept.append(item)
    return kept
