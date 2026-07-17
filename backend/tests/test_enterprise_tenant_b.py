"""Enterprise tenant B tests."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app
from app.modules.enterprise.email import render_enterprise_invite_email


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _dev_login(
    client: AsyncClient,
    email: str,
    *,
    plan_tier: str = "pro",
    seed_org: str | None = None,
) -> str:
    body: dict = {
        "email": email,
        "display_name": email.split("@")[0],
        "plan_tier": plan_tier,
    }
    if seed_org:
        body["seed_org"] = seed_org
    r = await client.post("/api/v1/auth/dev-login", json=body)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_provision_makes_admin_enterprise(client: AsyncClient):
    email = f"ent-admin-{uuid.uuid4().hex[:8]}@example.com"
    token = await _dev_login(client, email, plan_tier="pro")
    slug = f"ent-{uuid.uuid4().hex[:8]}"

    prov = await client.post(
        "/api/v1/ops/enterprise/provision",
        json={"company_name": "Test Co", "slug": slug, "admin_email": email},
    )
    assert prov.status_code == 200, prov.text
    org_id = prov.json()["org_id"]

    me = await client.get("/api/v1/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["plan_tier"] == "enterprise"
    memberships = me.json()["org_memberships"]
    assert any(m["org_id"] == org_id and m["is_primary_admin"] for m in memberships)


@pytest.mark.asyncio
async def test_non_primary_cannot_invite(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(get_settings(), "resend_api_key", None)
    monkeypatch.setattr(get_settings(), "smtp_host", None)
    monkeypatch.setattr(get_settings(), "smtp_username", None)
    monkeypatch.setattr(get_settings(), "smtp_password", None)
    admin_email = f"ent-a-{uuid.uuid4().hex[:8]}@example.com"
    member_email = f"ent-m-{uuid.uuid4().hex[:8]}@example.com"
    admin_token = await _dev_login(client, admin_email)
    slug = f"ent-{uuid.uuid4().hex[:8]}"

    prov = await client.post(
        "/api/v1/ops/enterprise/provision",
        json={"company_name": "Invite Co", "slug": slug, "admin_email": admin_email},
    )
    assert prov.status_code == 200, prov.text
    org_id = prov.json()["org_id"]

    inv = await client.post(
        f"/api/v1/enterprise/orgs/{org_id}/invites",
        headers=_auth(admin_token),
        json={"email": member_email, "expires_days": 7},
    )
    assert inv.status_code == 200, inv.text
    assert inv.json()["email_sent"] is False
    invite_token = inv.json()["token"]

    member_token = await _dev_login(client, member_email, plan_tier="free")
    accepted = await client.post(
        f"/api/v1/enterprise/invites/{invite_token}/accept",
        headers=_auth(member_token),
    )
    assert accepted.status_code == 200, accepted.text

    me_m = await client.get("/api/v1/me", headers=_auth(member_token))
    assert me_m.json()["plan_tier"] == "enterprise"

    # Member cannot create enterprise invite
    bad = await client.post(
        f"/api/v1/enterprise/orgs/{org_id}/invites",
        headers=_auth(member_token),
        json={"email": "other@example.com"},
    )
    assert bad.status_code == 403
    assert bad.json()["detail"] == "NOT_PRIMARY_ADMIN"


@pytest.mark.asyncio
async def test_accept_email_mismatch_and_remove_downgrade(client: AsyncClient):
    admin_email = f"ent-b-{uuid.uuid4().hex[:8]}@example.com"
    target_email = f"ent-target-{uuid.uuid4().hex[:8]}@example.com"
    wrong_email = f"ent-wrong-{uuid.uuid4().hex[:8]}@example.com"
    admin_token = await _dev_login(client, admin_email)
    slug = f"ent-{uuid.uuid4().hex[:8]}"

    prov = await client.post(
        "/api/v1/ops/enterprise/provision",
        json={"company_name": "Remove Co", "slug": slug, "admin_email": admin_email},
    )
    org_id = prov.json()["org_id"]

    inv = await client.post(
        f"/api/v1/enterprise/orgs/{org_id}/invites",
        headers=_auth(admin_token),
        json={"email": target_email},
    )
    invite_token = inv.json()["token"]

    wrong_token = await _dev_login(client, wrong_email, plan_tier="pro")
    mismatch = await client.post(
        f"/api/v1/enterprise/invites/{invite_token}/accept",
        headers=_auth(wrong_token),
    )
    assert mismatch.status_code == 403
    assert mismatch.json()["detail"] == "INVITE_EMAIL_MISMATCH"

    target_token = await _dev_login(client, target_email, plan_tier="pro")
    ok = await client.post(
        f"/api/v1/enterprise/invites/{invite_token}/accept",
        headers=_auth(target_token),
    )
    assert ok.status_code == 200, ok.text
    me_before = await client.get("/api/v1/me", headers=_auth(target_token))
    assert me_before.json()["plan_tier"] == "enterprise"
    target_id = me_before.json()["id"]

    removed = await client.delete(
        f"/api/v1/enterprise/orgs/{org_id}/members/{target_id}",
        headers=_auth(admin_token),
    )
    assert removed.status_code == 204, removed.text

    me_after = await client.get("/api/v1/me", headers=_auth(target_token))
    assert me_after.json()["plan_tier"] == "pro"  # restored plan_before


@pytest.mark.asyncio
async def test_ops_token_required_when_configured(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "enterprise_ops_token", "secret-ops")
    monkeypatch.setattr(settings, "allow_dev_login", False)

    r = await client.post(
        "/api/v1/ops/enterprise/provision",
        json={
            "company_name": "Nope",
            "slug": f"nope-{uuid.uuid4().hex[:6]}",
            "admin_email": "x@example.com",
        },
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "OPS_UNAUTHORIZED"

    # wrong token
    r2 = await client.post(
        "/api/v1/ops/enterprise/provision",
        headers={"X-Ops-Token": "wrong"},
        json={
            "company_name": "Nope",
            "slug": f"nope-{uuid.uuid4().hex[:6]}",
            "admin_email": "x@example.com",
        },
    )
    assert r2.status_code == 401


def test_enterprise_invite_email_template_escapes_dynamic_values():
    from datetime import UTC, datetime

    subject, html, text = render_enterprise_invite_email(
        org_name="<Acme & Co>",
        inviter_name='<Admin "A">',
        join_url='https://app.example/join?token="unsafe"&x=1',
        expires_at=datetime(2026, 7, 30, tzinfo=UTC),
    )

    assert subject == "<Acme & Co> 邀請你加入 BSChat"
    assert "&lt;Acme &amp; Co&gt;" in html
    assert "&lt;Admin &quot;A&quot;&gt;" in html
    assert 'token=&quot;unsafe&quot;&amp;x=1' in html
    assert "<Acme & Co>" in text
    assert "2026/07/30" in text
