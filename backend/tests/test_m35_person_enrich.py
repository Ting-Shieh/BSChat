import types
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.m3_5_person.service import (
    person_data_source,
    person_provenance_label,
    person_search_is_mock,
)


def _fake_enrichment(*, source_type: str, linkedin_url: str | None, confidence: float = 0.82):
    return types.SimpleNamespace(
        source_type=source_type,
        linkedin_url=linkedin_url,
        person_scope="可能負責 OEM 通路",
        confidence=confidence,
    )


def test_mock_mode_never_emits_linkedin_data_source():
    """紅旗 2：未接官方 LinkedIn API（mock）時，禁止輸出 ✦ LinkedIn 級來源。"""
    assert person_search_is_mock() is True  # 預設 person_search_provider=mock

    # linkedin_url / people_api(有 url) 在 mock 下都必須降級為 card_inference
    for st, url in (("linkedin_url", "https://linkedin.com/in/x"),
                    ("people_api", "https://linkedin.com/in/x")):
        e = _fake_enrichment(source_type=st, linkedin_url=url)
        assert person_data_source(e) == "card_inference"
        label = person_provenance_label(e)
        assert "✦ LinkedIn" not in label
        assert "名片推估" in label


def test_card_inference_and_web_labels_are_honest():
    card = _fake_enrichment(source_type="card_inference", linkedin_url=None)
    assert person_data_source(card) == "card_inference"
    assert "✦ LinkedIn" not in person_provenance_label(card)

    # web_search（Gemini 公開搜尋）是真實公開資料，誠實標「依連結公開摘要」，非 ✦ LinkedIn
    web = _fake_enrichment(source_type="web_search", linkedin_url="https://linkedin.com/in/x")
    assert person_data_source(web) == "linkedin_url_public"
    assert "✦ LinkedIn" not in person_provenance_label(web)


async def _login(client: AsyncClient, email: str) -> str:
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": email, "display_name": "M35 Test"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_person_enrich_blocked_on_free():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, f"m35-free-{uuid.uuid4()}@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:Pro Test
ORG:Acme Corp
TITLE:Manager
URL:https://www.linkedin.com/in/pro-test-user
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"m35-{uuid.uuid4()}"},
        )
        assert imp.status_code == 201
        card_id = imp.json()["raw_card_id"]
        await client.patch(
            f"/api/v1/cards/{card_id}/review",
            headers=headers,
            json={"name": "Pro Test", "company": "Acme Corp", "title": "Manager", "version": 1},
        )
        listed = await client.get("/api/v1/contacts", headers=headers)
        contact_id = listed.json()["items"][0]["id"]

        detail = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
        assert detail.json()["sections"]["ai_inferred"]["person_enrich"]["status"] == "locked"

        resp = await client.post(f"/api/v1/contacts/{contact_id}/person-enrich", headers=headers, json={})
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_switch_to_pro_unlocks_person_enrich_section():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _login(client, f"m35-pro-{uuid.uuid4()}@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        plan = await client.post("/api/v1/me/plan", headers=headers, json={"plan_tier": "pro"})
        assert plan.status_code == 200
        assert plan.json()["plan_tier"] == "pro"

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:Pro User
ORG:Beta Inc
TITLE:Director
URL:https://www.linkedin.com/in/pro-user-demo
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"m35p-{uuid.uuid4()}"},
        )
        await client.patch(
            f"/api/v1/cards/{imp.json()['raw_card_id']}/review",
            headers=headers,
            json={"name": "Pro User", "company": "Beta Inc", "title": "Director", "version": 1},
        )
        contact_id = (await client.get("/api/v1/contacts", headers=headers)).json()["items"][0]["id"]
        detail = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
        pe = detail.json()["sections"]["ai_inferred"]["person_enrich"]
        assert pe["is_pro"] is True
        assert pe["status"] in ("never", "pending", "completed")
