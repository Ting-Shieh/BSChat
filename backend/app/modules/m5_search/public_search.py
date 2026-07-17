"""M5b cross-pool search helpers (Pool A + public directory)."""

from app.core.entitlements import can_use_public_recommend
from app.models.user import UserEntitlement

ALLOWED_SEARCH_SCOPES = frozenset({"private", "network", "all"})


def can_use_network_scope(plan_tier: str) -> bool:
    """Deprecated: prefer can_use_public_recommend(ent) — Free has lifetime trials."""
    return plan_tier in ("pro", "enterprise")


def can_include_public_pool(ent: UserEntitlement) -> bool:
    return can_use_public_recommend(ent)