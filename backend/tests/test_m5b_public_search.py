"""M5b: Pro cross-pool search (public directory)."""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import async_session_factory
from app.main import app
from app.modules.m11_public_directory.index_builder import index_stub


async def _login(
    client: AsyncClient,
    *,
    email: str | None = None,
    plan_tier: str = "pro",
    seed_org: str | None = None,
) -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={
            "email": email or f"m5b-{uuid.uuid4()}@example.com",
            "display_name": "M5b Test",
            "plan_tier": plan_tier,
            "seed_org": seed_org,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _sync_public_index(monkeypatch):
    async def _index_now(stub_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await index_stub(db, stub_id)

    def enqueue_index(stub_id: uuid.UUID) -> None:
        asyncio.get_running_loop().create_task(_index_now(stub_id))

    monkeypatch.setattr(
        "app.modules.m11_public_directory.service.enqueue_stub_index",
        enqueue_index,
    )
    monkeypatch.setattr(
        "app.workers.tasks.public_directory_index.enqueue_stub_index",
        enqueue_index,
    )


async def _ensure_published_indexed() -> None:
    from sqlalchemy import select

    from app.models.public_business_stub import PublicBusinessStub

    async with async_session_factory() as db:
        result = await db.execute(
            select(PublicBusinessStub).where(PublicBusinessStub.status == "published")
        )
        for stub in result.scalars():
            await index_stub(db, stub.id)


@pytest.mark.asyncio
async def test_m5b_pro_network_search(monkeypatch):
    _sync_public_index(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(
            client,
            email=f"acme-publisher-{uuid.uuid4()}@example.com",
            plan_tier="enterprise",
            seed_org="acme-demo",
        )
        await _ensure_published_indexed()

        pro_token = await _login(client, plan_tier="pro")
        headers = {"Authorization": f"Bearer {pro_token}"}

        resp = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "誰做工業電腦或嵌入式的", "search_scope": "network"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "COMPLETED"
        assert body["result_count"] >= 1
        public = [r for r in body["results"] if r["source_pool"] == "public_directory"]
        assert public
        assert public[0]["stub_id"]
        assert public[0]["external_card_url"]
        assert public[0]["contact_preview"] is None
        assert "公開商務" in public[0]["match_reason"]


@pytest.mark.asyncio
async def test_m5b_free_network_forbidden():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, plan_tier="free")
        resp = await client.post(
            "/api/v1/search/queries",
            headers={"Authorization": f"Bearer {token}"},
            json={"query_text": "工業電腦", "search_scope": "network"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "SEARCH_SCOPE_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_m5b_all_scope_merges_pools(monkeypatch):
    _sync_public_index(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(
            client,
            email=f"acme-publisher2-{uuid.uuid4()}@example.com",
            plan_tier="enterprise",
            seed_org="acme-demo",
        )
        await _ensure_published_indexed()

        pro_token = await _login(client, plan_tier="pro")
        headers = {"Authorization": f"Bearer {pro_token}"}

        resp = await client.post(
            "/api/v1/search/queries",
            headers=headers,
            json={"query_text": "嵌入式", "search_scope": "all"},
        )
        assert resp.status_code == 200, resp.text
        pools = {r["source_pool"] for r in resp.json().get("results", [])}
        assert "public_directory" in pools
