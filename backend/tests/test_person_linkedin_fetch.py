import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.pipelines.person_enrich import PersonCandidate, fetch_by_url
from app.ai.pipelines.person_linkedin_web import (
    _parse_lookup_json,
    extract_linkedin_vanity,
    fetch_profile_via_web_search,
)


def test_extract_linkedin_vanity():
    assert extract_linkedin_vanity("https://www.linkedin.com/in/boxunshao/") == "boxunshao"


def test_parse_lookup_json():
    raw = json.dumps(
        {
            "headline": "Business Development @ ADATA",
            "summary": "Leads enterprise memory channel partnerships.",
            "confidence": 0.82,
            "matched_url": True,
        }
    )
    lookup = _parse_lookup_json(raw)
    assert lookup is not None
    assert lookup.headline.startswith("Business")
    assert lookup.confidence == 0.82


@pytest.mark.asyncio
async def test_fetch_by_url_returns_none_when_web_disabled():
    with patch(
        "app.ai.pipelines.person_linkedin_web.fetch_profile_via_web_search",
        new_callable=AsyncMock,
        return_value=None,
    ):
        candidate = await fetch_by_url(
            "https://www.linkedin.com/in/boxunshao/",
            name="邵柏勛",
            title="業務",
            company_name="威剛科技",
        )
    assert candidate is None


@pytest.mark.asyncio
async def test_fetch_by_url_uses_web_fallback(monkeypatch):
    fake = PersonCandidate(
        linkedin_url="https://www.linkedin.com/in/boxunshao/",
        headline="BD @ ADATA",
        summary="Enterprise SSD partnerships.",
        match_score=1.0,
        match_inputs={"source": "web_search"},
        source_type="web_search",
    )

    with patch(
        "app.ai.pipelines.person_linkedin_web.fetch_profile_via_web_search",
        new_callable=AsyncMock,
        return_value=fake,
    ):
        candidate = await fetch_by_url(
            "https://www.linkedin.com/in/boxunshao/",
            name="邵柏勛",
        )

    assert candidate is not None
    assert candidate.source_type == "web_search"


@pytest.mark.asyncio
async def test_fetch_profile_via_web_search_parses_gemini_response(monkeypatch):
    monkeypatch.setenv("PERSON_LINKEDIN_WEB_FALLBACK", "true")
    monkeypatch.setenv("PERSON_ENRICH_USE_MOCK", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    gemini_json = json.dumps(
        {
            "headline": "Sales Manager at ADATA",
            "summary": "Focus on B2B memory and SSD channels in Taiwan.",
            "confidence": 0.8,
            "matched_url": True,
        }
    )

    with patch(
        "app.ai.pipelines.person_linkedin_web.gemini_generate_with_google_search",
        new_callable=AsyncMock,
        return_value=(gemini_json, ["https://www.linkedin.com/in/boxunshao"]),
    ):
        if not get_settings().gemini_api_key:
            pytest.skip("GEMINI_API_KEY not configured")
        candidate = await fetch_profile_via_web_search(
            "https://www.linkedin.com/in/boxunshao/",
            name="邵柏勛",
            company_name="威剛科技",
            title="業務",
        )

    assert candidate is not None
    assert candidate.source_type == "web_search"
    assert "ADATA" in (candidate.headline or candidate.summary or "")


@pytest.mark.asyncio
async def test_person_enrich_web_source_completed(monkeypatch):
    from app.ai.schemas.person_scope_output import PersonScopeOutput
    from app.modules.m3_5_person import service as m35_service

    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_index", lambda _id: None)
    monkeypatch.setattr(
        "app.workers.tasks.person_enrich.enqueue_person_enrich_url_auto",
        lambda *_a, **_k: None,
    )

    web_candidate = PersonCandidate(
        linkedin_url="https://www.linkedin.com/in/boxunshao/",
        headline="BD @ ADATA",
        summary="Enterprise SSD channel sales.",
        match_score=1.0,
        source_type="web_search",
    )
    monkeypatch.setattr(
        "app.modules.m3_5_person.service.fetch_by_url",
        AsyncMock(return_value=web_candidate),
    )
    monkeypatch.setattr(
        "app.modules.m3_5_person.service.summarize_person_scope",
        AsyncMock(
            return_value=(
                PersonScopeOutput(scope="可能負責企業 SSD 通路業務", confidence=0.78),
                "gemini-test",
                "v1",
            )
        ),
    )

    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": f"web-li-{uuid.uuid4()}@example.com", "display_name": "Web LI"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/v1/me/plan", headers=headers, json={"plan_tier": "pro"})

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:邵柏勛
ORG:威剛科技
TITLE:業務
URL:https://www.linkedin.com/in/boxunshao/
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"web-{uuid.uuid4()}"},
        )
        card_id = imp.json()["raw_card_id"]
        await client.patch(
            f"/api/v1/cards/{card_id}/review",
            headers=headers,
            json={"name": "邵柏勛", "company": "威剛科技", "title": "業務", "version": 1},
        )
        contact_id = (await client.get("/api/v1/contacts", headers=headers)).json()["items"][0]["id"]

        resp = await client.post(
            f"/api/v1/contacts/{contact_id}/person-enrich",
            headers=headers,
            json={},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert body["data_source"] == "linkedin_url_public"
        assert body.get("quota_remaining") == 19

        detail = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
        pe = detail.json()["sections"]["ai_inferred"]["person_enrich"]
        assert pe["status"] == "completed"
        assert pe["data_source"] == "linkedin_url_public"
        assert "公開摘要" in (pe.get("provenance_label") or "")


@pytest.mark.asyncio
async def test_manual_person_enrich_after_url_auto_consumes_quota(monkeypatch):
    """Manual refresh must re-run and consume quota even if url_auto already enriched."""
    from app.ai.schemas.person_scope_output import PersonScopeOutput
    from app.modules.m3_5_person import service as m35_service

    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_index", lambda _id: None)
    monkeypatch.setattr(
        "app.workers.tasks.person_enrich.enqueue_person_enrich_url_auto",
        lambda *_a, **_k: None,
    )

    web_candidate = PersonCandidate(
        linkedin_url="https://www.linkedin.com/in/boxunshao/",
        headline="BD @ ADATA",
        summary="Enterprise SSD channel sales.",
        match_score=1.0,
        source_type="web_search",
    )
    monkeypatch.setattr(
        "app.modules.m3_5_person.service.fetch_by_url",
        AsyncMock(return_value=web_candidate),
    )
    monkeypatch.setattr(
        "app.modules.m3_5_person.service.summarize_person_scope",
        AsyncMock(
            return_value=(
                PersonScopeOutput(scope="可能負責企業 SSD 通路業務", confidence=0.78),
                "gemini-test",
                "v1",
            )
        ),
    )

    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": f"url-auto-{uuid.uuid4()}@example.com", "display_name": "URL Auto"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/v1/me/plan", headers=headers, json={"plan_tier": "pro"})

        me_before = await client.get("/api/v1/me", headers=headers)
        quota_before = me_before.json()["quotas"]["person_linkedin_remaining_month"]

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:邵柏勛
ORG:威剛科技
TITLE:業務
URL:https://www.linkedin.com/in/boxunshao/
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"url-auto-{uuid.uuid4()}"},
        )
        card_id = imp.json()["raw_card_id"]
        await client.patch(
            f"/api/v1/cards/{card_id}/review",
            headers=headers,
            json={"name": "邵柏勛", "company": "威剛科技", "title": "業務", "version": 1},
        )
        contact_id = (await client.get("/api/v1/contacts", headers=headers)).json()["items"][0]["id"]

        me = await client.get("/api/v1/me", headers=headers)
        user_id = me.json()["id"]
        await m35_service.run_person_enrich_url_auto(
            {"contact_id": str(contact_id), "user_id": str(user_id)}
        )

        me_mid = await client.get("/api/v1/me", headers=headers)
        assert me_mid.json()["quotas"]["person_linkedin_remaining_month"] == quota_before

        resp = await client.post(
            f"/api/v1/contacts/{contact_id}/person-enrich",
            headers=headers,
            json={},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert body.get("quota_remaining") == quota_before - 1

        me_after = await client.get("/api/v1/me", headers=headers)
        assert me_after.json()["quotas"]["person_linkedin_remaining_month"] == quota_before - 1


@pytest.mark.asyncio
async def test_person_enrich_linkedin_url_fetch_fail_no_card_fallback(monkeypatch):
    monkeypatch.setattr("app.modules.m3_contacts.upsert.enqueue_contact_index", lambda _id: None)
    monkeypatch.setattr(
        "app.workers.tasks.person_enrich.enqueue_person_enrich_url_auto",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "app.modules.m3_5_person.service.fetch_by_url",
        AsyncMock(return_value=None),
    )

    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/dev-login",
            json={"email": f"li-fail-{uuid.uuid4()}@example.com", "display_name": "LI Fail"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/v1/me/plan", headers=headers, json={"plan_tier": "pro"})

        vcard = """BEGIN:VCARD
VERSION:3.0
FN:邵柏勛
ORG:威剛科技
TITLE:業務
URL:https://www.linkedin.com/in/boxunshao/
END:VCARD"""
        imp = await client.post(
            "/api/v1/cards/import-qr",
            json={"payload": vcard},
            headers={**headers, "Idempotency-Key": f"li-{uuid.uuid4()}"},
        )
        card_id = imp.json()["raw_card_id"]
        await client.patch(
            f"/api/v1/cards/{card_id}/review",
            headers=headers,
            json={"name": "邵柏勛", "company": "威剛科技", "title": "業務", "version": 1},
        )
        contact_id = (await client.get("/api/v1/contacts", headers=headers)).json()["items"][0]["id"]

        resp = await client.post(
            f"/api/v1/contacts/{contact_id}/person-enrich",
            headers=headers,
            json={},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "insufficient"
        assert "無法從公開網路" in (body.get("message") or "")

        detail = await client.get(f"/api/v1/contacts/{contact_id}", headers=headers)
        pe = detail.json()["sections"]["ai_inferred"]["person_enrich"]
        assert pe["status"] == "insufficient"
        assert not pe.get("person_scope")
