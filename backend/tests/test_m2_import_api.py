import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_import_qr_vcard_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": "m2-import@example.com", "display_name": "Import Test"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]

        payload = """BEGIN:VCARD
VERSION:3.0
FN:電子名片測試
ORG:BSChat Demo Co
TITLE:Solution Architect
TEL:02-12345678
EMAIL:demo@bschat.example
END:VCARD"""

        resp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": payload},
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": f"test-qr-{uuid.uuid4()}",
            },
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["capture_method"] == "qr"
        assert data["status"] == "ocr_done"
        assert data["extracted_preview"]["name"] == "電子名片測試"

        card = await client.get(
            f"/api/v1/cards/{data['raw_card_id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert card.status_code == 200
        assert card.json()["ocr_result"]["engine"] == "import"


@pytest.mark.asyncio
async def test_import_qr_idempotent_restores_contact_after_delete():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": f"qr-restore-{uuid.uuid4()}@example.com", "display_name": "QR Restore"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        idem = f"qr-restore-{uuid.uuid4()}"

        payload = """BEGIN:VCARD
VERSION:3.0
FN:QR還原測試
ORG:Restore Co
TITLE:PM
EMAIL:restore@bschat.example
END:VCARD"""

        first = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": payload},
            headers={**headers, "Idempotency-Key": idem},
        )
        assert first.status_code == 201
        card_id = first.json()["raw_card_id"]

        contacts = await client.get("/api/v1/contacts", headers=headers)
        assert any(c["display_name"] == "QR還原測試" for c in contacts.json()["items"])

        deleted = await client.delete(f"/api/v1/cards/{card_id}", headers=headers)
        assert deleted.status_code == 204

        contacts_after_delete = await client.get("/api/v1/contacts", headers=headers)
        assert not any(c["display_name"] == "QR還原測試" for c in contacts_after_delete.json()["items"])

        again = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": payload},
            headers={**headers, "Idempotency-Key": idem},
        )
        assert again.status_code == 201

        contacts_restored = await client.get("/api/v1/contacts", headers=headers)
        assert any(c["display_name"] == "QR還原測試" for c in contacts_restored.json()["items"])

