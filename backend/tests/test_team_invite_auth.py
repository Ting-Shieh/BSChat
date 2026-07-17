"""Team invite + self-hosted auth mode tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _dev_login(client: AsyncClient, email: str, seed_org: str | None = None) -> str:
    body: dict = {"email": email, "display_name": email.split("@")[0], "plan_tier": "pro"}
    if seed_org:
        body["seed_org"] = seed_org
    r = await client.post("/api/v1/auth/dev-login", json=body)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_dev_login_can_be_disabled(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "allow_dev_login", False)
    r = await client.post(
        "/api/v1/auth/dev-login",
        json={"email": "blocked@example.com", "display_name": "Blocked"},
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "DEV_LOGIN_DISABLED"


@pytest.mark.asyncio
async def test_invite_create_preview_accept(client: AsyncClient):
    token_a = await _dev_login(client, "alice-invite2@example.com", seed_org="invite-demo-2")
    me = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token_a}"})
    assert me.status_code == 200
    orgs = me.json().get("org_memberships") or []
    assert orgs, me.json()
    org_id = orgs[0]["org_id"]

    created = await client.post(
        "/api/v1/invites",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"org_id": org_id, "expires_days": 7, "max_uses": 5},
    )
    assert created.status_code == 200, created.text
    invite_token = created.json()["token"]

    preview = await client.get(f"/api/v1/invites/{invite_token}")
    assert preview.status_code == 200

    token_b = await _dev_login(client, "bob-invite2@example.com")
    accepted = await client.post(
        f"/api/v1/invites/{invite_token}/accept",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert accepted.status_code == 200, accepted.text


@pytest.mark.asyncio
async def test_magic_link_dev_flow(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "allow_dev_login", True)
    monkeypatch.setattr(settings, "resend_api_key", None)
    monkeypatch.setattr(settings, "frontend_base_url", "http://localhost:3000")

    req = await client.post(
        "/api/v1/auth/magic-link",
        json={"email": "magic-user@example.com"},
    )
    assert req.status_code == 200, req.text
    data = req.json()
    assert data["sent"] is False
    assert data["debug_link"]
    assert "magic-link/verify" in data["debug_link"]

    # follow redirect disabled — just hit verify
    verify_path = data["debug_link"].split("http://test", 1)[-1]
    if verify_path.startswith("http"):
        # debug_link uses API_BASE_URL from settings, not test host
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(data["debug_link"])
        token = parse_qs(parsed.query).get("token", [None])[0]
        assert token
        verify = await client.get(
            f"/api/v1/auth/magic-link/verify?token={token}",
            follow_redirects=False,
        )
    else:
        verify = await client.get(verify_path, follow_redirects=False)
    assert verify.status_code in (302, 307)
    loc = verify.headers.get("location", "")
    assert "access_token=" in loc
    assert "/auth/callback" in loc


@pytest.mark.asyncio
async def test_auth_mode_endpoint(client: AsyncClient):
    r = await client.get("/api/v1/auth/auth-mode")
    assert r.status_code == 200
    data = r.json()
    assert "allow_dev_login" in data
    assert "google_enabled" in data
    assert "email_magic_link_enabled" in data
