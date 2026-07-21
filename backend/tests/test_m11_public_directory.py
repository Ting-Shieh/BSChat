"""M11 enterprise public directory API tests."""

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.db import async_session_factory
from app.main import app
from app.models.public_directory_document import PublicDirectoryDocument
from app.modules.m11_public_directory.index_builder import index_stub, unindex_stub


async def _login(
    client: AsyncClient,
    *,
    email: str | None = None,
    plan_tier: str = "enterprise",
    seed_org: str | None = "acme-demo",
) -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={
            "email": email or f"m11-{uuid.uuid4()}@example.com",
            "display_name": "M11 Admin",
            "plan_tier": plan_tier,
            "seed_org": seed_org,
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _sync_index(monkeypatch):
    async def _index_now(stub_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await index_stub(db, stub_id)

    async def _unindex_now(stub_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await unindex_stub(db, stub_id)

    def enqueue_index(stub_id: uuid.UUID) -> None:
        asyncio.get_running_loop().create_task(_index_now(stub_id))

    def enqueue_unindex(stub_id: uuid.UUID) -> None:
        asyncio.get_running_loop().create_task(_unindex_now(stub_id))

    monkeypatch.setattr(
        "app.modules.m11_public_directory.service.enqueue_stub_index",
        enqueue_index,
    )
    monkeypatch.setattr(
        "app.modules.m11_public_directory.service.enqueue_stub_unindex",
        enqueue_unindex,
    )
    monkeypatch.setattr(
        "app.workers.tasks.public_directory_index.enqueue_stub_index",
        enqueue_index,
    )
    monkeypatch.setattr(
        "app.workers.tasks.public_directory_index.enqueue_stub_unindex",
        enqueue_unindex,
    )


async def _get_org_id(client: AsyncClient, headers: dict) -> str:
    orgs = await client.get("/api/v1/orgs/mine", headers=headers)
    assert orgs.status_code == 200, orgs.text
    items = orgs.json()["items"]
    assert items, "expected seeded org"
    return items[0]["id"]


@pytest.mark.asyncio
async def test_m11_stub_crud_publish_index(monkeypatch):
    # Avoid async enqueue race; index synchronously in assertions.
    monkeypatch.setattr(
        "app.modules.m11_public_directory.service.enqueue_stub_index",
        lambda _stub_id: None,
    )
    monkeypatch.setattr(
        "app.modules.m11_public_directory.service.enqueue_stub_unindex",
        lambda _stub_id: None,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, seed_org=None)
        headers = {"Authorization": f"Bearer {token}"}

        orgs = await client.get("/api/v1/orgs/mine", headers=headers)
        assert orgs.status_code == 200
        assert orgs.json()["items"] == []

        seed = await client.post(
            "/api/v1/auth/dev-login",
            json={
                "email": f"m11-seed-{uuid.uuid4()}@example.com",
                "plan_tier": "enterprise",
                "seed_org": "acme-demo",
            },
        )
        token = seed.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        org_id = await _get_org_id(client, headers)

        create = await client.post(
            f"/api/v1/orgs/{org_id}/stubs",
            headers=headers,
            json={
                "display_name": "測試窗口",
                "company_name": "Test Corp",
                "title": "PM",
                "responsibility_keywords": ["通路"],
                "product_keywords": ["工控"],
                "external_card_url": "https://example.com/card/test",
                "allow_ai_recommend": False,
            },
        )
        assert create.status_code == 201, create.text
        stub_id = create.json()["id"]
        assert create.json()["status"] == "draft"

        # Explicit draft → bind owner + publish
        me = await client.get("/api/v1/me", headers=headers)
        owner_id = me.json()["id"]
        draft = await client.post(
            f"/api/v1/orgs/{org_id}/stubs",
            headers=headers,
            json={
                "display_name": "草稿窗口",
                "company_name": "Test Corp",
                "product_keywords": ["工控"],
                "external_card_url": "https://example.com/card/draft",
                "allow_ai_recommend": False,
                "owner_user_id": owner_id,
            },
        )
        assert draft.status_code == 201, draft.text
        assert draft.json()["status"] == "draft"
        draft_id = draft.json()["id"]

        publish = await client.post(
            f"/api/v1/orgs/{org_id}/stubs/{draft_id}/publish",
            headers=headers,
        )
        assert publish.status_code == 200, publish.text
        assert publish.json()["status"] == "published"

        async with async_session_factory() as db:
            await index_stub(db, uuid.UUID(draft_id))
        async with async_session_factory() as db:
            doc = await db.scalar(
                select(PublicDirectoryDocument).where(
                    PublicDirectoryDocument.stub_id == uuid.UUID(draft_id)
                )
            )
            assert doc is not None
            assert "工控" in doc.search_text

        unpublish = await client.post(
            f"/api/v1/orgs/{org_id}/stubs/{draft_id}/unpublish",
            headers=headers,
        )
        assert unpublish.status_code == 200, unpublish.text

        async with async_session_factory() as db:
            from app.modules.m11_public_directory.index_builder import unindex_stub

            await unindex_stub(db, uuid.UUID(draft_id))
        async with async_session_factory() as db:
            doc = await db.scalar(
                select(PublicDirectoryDocument).where(PublicDirectoryDocument.stub_id == uuid.UUID(draft_id))
            )
            assert doc is None


@pytest.mark.asyncio
async def test_m11_patch_published_reindexes(monkeypatch):
    reindex_calls: list[uuid.UUID] = []
    index_tasks: list[asyncio.Task] = []

    async def _index_now(stub_id: uuid.UUID) -> None:
        async with async_session_factory() as db:
            await index_stub(db, stub_id)

    def enqueue_index(stub_id: uuid.UUID) -> None:
        reindex_calls.append(stub_id)
        index_tasks.append(asyncio.get_running_loop().create_task(_index_now(stub_id)))

    monkeypatch.setattr(
        "app.modules.m11_public_directory.service.enqueue_stub_index",
        enqueue_index,
    )
    monkeypatch.setattr(
        "app.workers.tasks.public_directory_index.enqueue_stub_index",
        enqueue_index,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        org_id = await _get_org_id(client, headers)

        create = await client.post(
            f"/api/v1/orgs/{org_id}/stubs",
            headers=headers,
            json={
                "display_name": "可編輯窗口",
                "company_name": "Edit Corp",
                "product_keywords": ["舊關鍵字"],
                "external_card_url": "https://example.com/card/edit",
                "allow_ai_recommend": False,
                "owner_user_id": (await client.get("/api/v1/me", headers=headers)).json()["id"],
            },
        )
        assert create.status_code == 201, create.text
        stub_id = uuid.UUID(create.json()["id"])

        publish = await client.post(
            f"/api/v1/orgs/{org_id}/stubs/{stub_id}/publish",
            headers=headers,
        )
        assert publish.status_code == 200, publish.text
        if index_tasks:
            await asyncio.gather(*index_tasks)
            index_tasks.clear()
        reindex_calls.clear()

        patch = await client.patch(
            f"/api/v1/orgs/{org_id}/stubs/{stub_id}",
            headers=headers,
            json={
                "display_name": "更新後窗口",
                "product_keywords": ["新產品線"],
            },
        )
        assert patch.status_code == 200, patch.text
        assert patch.json()["display_name"] == "更新後窗口"
        assert stub_id in reindex_calls
        if index_tasks:
            await asyncio.gather(*index_tasks)
            index_tasks.clear()

        async with async_session_factory() as db:
            doc = await db.scalar(
                select(PublicDirectoryDocument).where(PublicDirectoryDocument.stub_id == stub_id)
            )
            assert doc is not None
            assert "新產品線" in doc.search_text
            assert "舊關鍵字" not in doc.search_text


@pytest.mark.asyncio
async def test_m11_enterprise_gate():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client, plan_tier="pro", seed_org=None)
        await client.post("/api/v1/me/plan", headers={"Authorization": f"Bearer {token}"}, json={"plan_tier": "pro"})
        fake_org = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/orgs/{fake_org}/stubs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert resp.json()["detail"] == "ENTERPRISE_REQUIRED"


@pytest.mark.asyncio
async def test_m11_invalid_external_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        org_id = await _get_org_id(client, headers)

        resp = await client.post(
            f"/api/v1/orgs/{org_id}/stubs",
            headers=headers,
            json={
                "display_name": "Bad URL",
                "company_name": "Test",
                "external_card_url": "not-a-url",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "INVALID_EXTERNAL_URL"


@pytest.mark.asyncio
async def test_m11_dev_seed_has_published_stubs(monkeypatch):
    _sync_index(monkeypatch)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        org_id = await _get_org_id(client, headers)

        stubs = await client.get(f"/api/v1/orgs/{org_id}/stubs", headers=headers)
        assert stubs.status_code == 200
        published = [s for s in stubs.json()["items"] if s["status"] == "published"]
        assert len(published) >= 3

        me = await client.get("/api/v1/me", headers=headers)
        assert me.status_code == 200
        assert len(me.json()["org_memberships"]) >= 1
