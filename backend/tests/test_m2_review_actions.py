import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _login(client: AsyncClient, email: str) -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": email, "display_name": "Review Test"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_import_qr_then_skip_and_delete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, f"review-skip-{uuid.uuid4()}@example.com")

        payload = """BEGIN:VCARD
VERSION:3.0
FN:待確認測試
ORG:Skip Co
TEL:02-12345678
EMAIL:skip@bschat.example
END:VCARD"""
        resp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": payload},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"skip-{uuid.uuid4()}",
            },
        )
        assert resp.status_code == 201, resp.text
        card_id = resp.json()["raw_card_id"]
        card_detail = await client.get(
            f"/api/v1/cards/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert card_detail.json()["review_status"] == "pending_review"

        pending = await client.get(
            "/api/v1/cards/pending-count",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pending.status_code == 200
        before = pending.json()["count"]
        assert before >= 1

        skip = await client.post(
            f"/api/v1/cards/{card_id}/skip",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert skip.status_code == 200, skip.text
        assert skip.json()["review_deferred_at"] is not None

        pending_after_skip = await client.get(
            "/api/v1/cards/pending-count",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert pending_after_skip.json()["count"] == before - 1

        contacts = await client.get(
            "/api/v1/contacts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert contacts.status_code == 200
        assert any(c["display_name"] == "待確認測試" for c in contacts.json()["items"])

        delete = await client.delete(
            f"/api/v1/cards/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete.status_code == 204

        contacts_after = await client.get(
            "/api/v1/contacts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert not any(c["display_name"] == "待確認測試" for c in contacts_after.json()["items"])

        gone = await client.get(
            f"/api/v1/cards/{card_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert gone.status_code == 404

        auto_payload = """BEGIN:VCARD
VERSION:3.0
FN:自動確認
ORG:Auto Co
TITLE:Director
TEL:02-11112222
EMAIL:auto@bschat.example
END:VCARD"""
        auto_resp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": auto_payload},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"auto-{uuid.uuid4()}",
            },
        )
        assert auto_resp.status_code == 201
        auto_id = auto_resp.json()["raw_card_id"]
        auto_card = await client.get(
            f"/api/v1/cards/{auto_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert auto_card.json()["review_status"] == "auto_accepted"

        skip_auto = await client.post(
            f"/api/v1/cards/{auto_id}/skip",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert skip_auto.status_code == 400
