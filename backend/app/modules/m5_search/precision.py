"""Search precision → rerank prompt guidance (PRD §11.9, DDR-101)."""

from app.models.user import UserEntitlement

SearchPrecision = str

DEFAULT_PRECISION = "balanced"
VALID_PRECISIONS = frozenset({"strict", "balanced", "exploratory"})

PRECISION_RERANK_GUIDANCE: dict[str, str] = {
    "strict": (
        "Search precision: STRICT — only return contacts you are highly confident match "
        "the query. Return fewer or zero results rather than weak or speculative matches."
    ),
    "balanced": (
        "Search precision: BALANCED — return semantically relevant contacts; "
        "interpret synonyms and industry language; include clear match_reason."
    ),
    "exploratory": (
        "Search precision: EXPLORATORY — include weaker but plausibly related contacts; "
        "still cite real candidate fields; rank stronger matches first."
    ),
}


def can_use_exploratory(plan_tier: str) -> bool:
    return plan_tier in ("pro", "enterprise")


def normalize_precision(value: str | None) -> SearchPrecision:
    if value in VALID_PRECISIONS:
        return value
    return DEFAULT_PRECISION


def precision_rerank_guidance(precision: str | None) -> str:
    mode = normalize_precision(precision)
    return PRECISION_RERANK_GUIDANCE[mode]


def validate_precision_update(plan_tier: str, precision: str) -> str:
    mode = normalize_precision(precision)
    if mode == "exploratory" and not can_use_exploratory(plan_tier):
        raise ValueError("SEARCH_PRECISION_NOT_ALLOWED")
    return mode


def precision_empty_hint(precision: str) -> str | None:
    if precision == "strict":
        return "目前為「精準」模式，可至設定改為「平衡」，或（Pro）試試「探索」"
    return None
