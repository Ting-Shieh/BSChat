import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _login(client: AsyncClient) -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": f"contact-edit-{uuid.uuid4()}@example.com", "display_name": "Edit Test"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_patch_contact_updates_fields(monkeypatch):
    dispatched: list[str] = []

    def fake_dispatch(c, *, trigger_type="ingest"):
        dispatched.append(trigger_type)

    monkeypatch.setattr(
        "app.modules.m3_contacts.upsert.dispatch_company_enrich",
        fake_dispatch,
    )
    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_index", lambda _id: None)
    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_inference", lambda *_a, **_k: None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:王小明
ORG:測試科技股份有限公司
TITLE:業務經理
TEL:0912345678
EMAIL:ming@test.com
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"edit-{uuid.uuid4()}"},
        )
        assert imp.status_code == 201, imp.text
        card_id = imp.json()["raw_card_id"]

        review = await client.patch(
            f"/api/v1/cards/{card_id}/review",
            headers=headers,
            json={
                "name": "王小明",
                "company": "測試科技股份有限公司",
                "title": "業務經理",
                "version": imp.json().get("version", 1),
            },
        )
        assert review.status_code == 200, review.text

        listed = await client.get("/api/v1/contacts", headers=headers)
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert len(items) >= 1
        contact_id = items[0]["id"]

        detail = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
        version = detail.json()["version"]

        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=headers,
            json={
                "version": version,
                "fields": {
                    "display_name": "王大明",
                    "company_name": "新創科技股份有限公司",
                    "title": "總監",
                },
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["display_name"] == "王大明"
        assert data["company_name"] == "新創科技股份有限公司"
        assert data["title"] == "總監"
        assert data["version"] == version + 1
        assert any(f["source"] == "manual" for f in data["sections"]["card_original"]["fields"])
        assert "company_name_changed" in dispatched

        conflict = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=headers,
            json={"version": version, "fields": {"display_name": "衝突測試"}},
        )
        assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_patch_person_scope_manual_pro(monkeypatch):
    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_index", lambda _id: None)
    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_inference", lambda *_a, **_k: None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        plan = await client.post("/api/v1/me/plan", headers=headers, json={"plan_tier": "pro"})
        assert plan.status_code == 200

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:手動職責
ORG:測試公司
TITLE:經理
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"scope-{uuid.uuid4()}"},
        )
        assert imp.status_code == 201
        await client.patch(
            f"/api/v1/cards/{imp.json()['raw_card_id']}/review",
            headers=headers,
            json={"name": "手動職責", "company": "測試公司", "title": "經理", "version": 1},
        )
        contact_id = (await client.get("/api/v1/contacts", headers=headers)).json()["items"][0]["id"]
        detail = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
        version = detail.json()["version"]

        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=headers,
            json={
                "version": version,
                "fields": {"person_scope": "企業 SSD 與記憶體通路"},
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        pe = data["sections"]["ai_inferred"]["person_enrich"]
        assert pe["status"] == "completed"
        assert pe["person_scope"] == "可能負責企業 SSD 與記憶體通路"
        assert pe["data_source"] == "user_manual"
        assert pe["provenance_label"] == "✎ 使用者筆記"

        cleared = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=headers,
            json={"version": data["version"], "fields": {"person_scope": ""}},
        )
        assert cleared.status_code == 200, cleared.text
        pe2 = cleared.json()["sections"]["ai_inferred"]["person_enrich"]
        assert pe2["status"] in ("never", "insufficient")
        assert not pe2.get("person_scope")


@pytest.mark.asyncio
async def test_patch_person_scope_blocked_on_free():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client)
        headers = {"Authorization": f"Bearer {token}"}

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:Free Scope
ORG:Co
TITLE:Mgr
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"free-scope-{uuid.uuid4()}"},
        )
        await client.patch(
            f"/api/v1/cards/{imp.json()['raw_card_id']}/review",
            headers=headers,
            json={"name": "Free Scope", "company": "Co", "title": "Mgr", "version": 1},
        )
        contact_id = (await client.get("/api/v1/contacts", headers=headers)).json()["items"][0]["id"]
        version = (await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)).json()["version"]

        resp = await client.patch(
            f"/api/v1/contacts/{contact_id}",
            headers=headers,
            json={"version": version, "fields": {"person_scope": "測試"}},
        )
        assert resp.status_code == 403

