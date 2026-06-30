"""M5b cross-pool search helpers (Pool A + public directory)."""

ALLOWED_SEARCH_SCOPES = frozenset({"private", "network", "all"})


def can_use_network_scope(plan_tier: str) -> bool:
    return plan_tier in ("pro", "enterprise")
