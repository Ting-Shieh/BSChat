"""Unit tests for Free public-recommend lifetime trial (M1 / DDR-M1)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.entitlements import (
    apply_plan_preset,
    can_use_public_recommend,
    consume_public_recommend,
    public_recommend_unlimited,
    remaining_public_recommend,
)


def _ent(**kwargs):
    base = dict(
        plan_tier="free",
        public_recommend_lifetime_quota=2,
        public_recommend_used_lifetime=0,
        person_enrich_mode="inference_only",
        person_linkedin_quota_monthly=0,
        person_linkedin_auto_on_url=False,
        auto_refresh_enabled=False,
        auto_refresh_interval_days=90,
        manual_refresh_quota_monthly=3,
        search_cache_daily_quota=30,
        live_augment_monthly_quota=5,
        search_precision="balanced",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_free_can_use_while_remaining():
    ent = _ent(public_recommend_used_lifetime=0)
    assert can_use_public_recommend(ent) is True
    assert remaining_public_recommend(ent) == 2


def test_free_exhausted():
    ent = _ent(public_recommend_used_lifetime=2)
    assert can_use_public_recommend(ent) is False
    assert remaining_public_recommend(ent) == 0


def test_pro_unlimited():
    ent = _ent(plan_tier="pro", public_recommend_used_lifetime=2)
    assert can_use_public_recommend(ent) is True
    assert public_recommend_unlimited(ent) is True
    assert remaining_public_recommend(ent) == -1


@pytest.mark.asyncio
async def test_consume_increments_free():
    ent = _ent()
    db = AsyncMock()
    left = await consume_public_recommend(db, ent)
    assert ent.public_recommend_used_lifetime == 1
    assert left == 1
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_consume_noop_for_pro():
    ent = _ent(plan_tier="pro")
    db = AsyncMock()
    left = await consume_public_recommend(db, ent)
    assert left == -1
    assert ent.public_recommend_used_lifetime == 0
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_raises_when_exhausted():
    ent = _ent(public_recommend_used_lifetime=2)
    db = AsyncMock()
    with pytest.raises(HTTPException) as ei:
        await consume_public_recommend(db, ent)
    assert ei.value.status_code == 403
    assert ei.value.detail == "PUBLIC_RECOMMEND_TRIAL_EXHAUSTED"


def test_plan_switch_preserves_used():
    ent = _ent(public_recommend_used_lifetime=1)
    apply_plan_preset(ent, "pro")
    assert ent.plan_tier == "pro"
    assert ent.public_recommend_used_lifetime == 1
    apply_plan_preset(ent, "free")
    assert ent.plan_tier == "free"
    assert ent.public_recommend_used_lifetime == 1
    assert can_use_public_recommend(ent) is True
    assert remaining_public_recommend(ent) == 1
