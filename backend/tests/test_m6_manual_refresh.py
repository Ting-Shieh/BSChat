"""M6 manual company re-enrich tests."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.entitlements import consume_manual_refresh_quota, manual_refresh_remaining
from app.main import app
from app.models.user import UserEntitlement


@pytest.mark.asyncio
async def test_manual_refresh_remaining_unlimited():
    ent = UserEntitlement(
        user_id=uuid.uuid4(),
        manual_refresh_quota_monthly=-1,
        manual_refresh_used_this_month=99,
    )
    assert manual_refresh_remaining(ent) == -1


@pytest.mark.asyncio
async def test_consume_manual_refresh_quota_exhausted():
    ent = UserEntitlement(
        user_id=uuid.uuid4(),
        manual_refresh_quota_monthly=3,
        manual_refresh_used_this_month=3,
        manual_refresh_reset_at=datetime.now(UTC),
    )
    db = AsyncMock()
    db.flush = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await consume_manual_refresh_quota(db, ent)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_re_enrich_company_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": f"m6-refresh-{uuid.uuid4()}@example.com", "display_name": "M6"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            f"/api/v1/companies/{uuid.uuid4()}/re-enrich",
            headers=headers,
        )
        assert resp.status_code == 404
