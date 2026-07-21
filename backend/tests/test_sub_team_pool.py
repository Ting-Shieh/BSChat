"""Sub-team contact visibility (DDR-v4-10/11)."""

import uuid

import pytest

from app.core.db import async_session_factory
from app.core.team import get_visible_capturer_ids
from app.models.organization import Organization, OrgMember
from app.models.sub_team import SubTeam, SubTeamMember
from app.models.user import User, Workspace


async def _mk_user(db) -> User:
    user = User(email=f"st-{uuid.uuid4()}@example.com", display_name="Member")
    db.add(user)
    await db.flush()
    db.add(Workspace(owner_user_id=user.id, name="Personal"))
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_non_enterprise_sees_only_self():
    async with async_session_factory() as db:
        org = Organization(name="Legacy", slug=f"leg-{uuid.uuid4().hex[:8]}", is_enterprise=False)
        db.add(org)
        await db.flush()
        alice = await _mk_user(db)
        bob = await _mk_user(db)
        db.add(OrgMember(org_id=org.id, user_id=alice.id, role="admin"))
        db.add(OrgMember(org_id=org.id, user_id=bob.id, role="member"))
        await db.commit()

        ids = set(await get_visible_capturer_ids(db, alice.id))
        assert ids == {alice.id}


@pytest.mark.asyncio
async def test_enterprise_without_subteam_sees_only_self():
    async with async_session_factory() as db:
        alice = await _mk_user(db)
        bob = await _mk_user(db)
        org = Organization(
            name="Ent",
            slug=f"ent-{uuid.uuid4().hex[:8]}",
            is_enterprise=True,
            primary_admin_user_id=alice.id,
        )
        db.add(org)
        await db.flush()
        db.add(OrgMember(org_id=org.id, user_id=alice.id, role="admin"))
        db.add(OrgMember(org_id=org.id, user_id=bob.id, role="member"))
        await db.commit()

        assert set(await get_visible_capturer_ids(db, alice.id)) == {alice.id}
        assert set(await get_visible_capturer_ids(db, bob.id)) == {bob.id}


@pytest.mark.asyncio
async def test_same_subteam_share_cross_team_isolated():
    async with async_session_factory() as db:
        lead = await _mk_user(db)
        a1 = await _mk_user(db)
        b1 = await _mk_user(db)
        org = Organization(
            name="Ent2",
            slug=f"ent2-{uuid.uuid4().hex[:8]}",
            is_enterprise=True,
            primary_admin_user_id=lead.id,
        )
        db.add(org)
        await db.flush()
        for u, role in ((lead, "admin"), (a1, "member"), (b1, "member")):
            db.add(OrgMember(org_id=org.id, user_id=u.id, role=role))

        t1 = SubTeam(org_id=org.id, name="業務一組", created_by_user_id=lead.id)
        t2 = SubTeam(org_id=org.id, name="業務二組", created_by_user_id=lead.id)
        db.add(t1)
        db.add(t2)
        await db.flush()
        db.add(SubTeamMember(sub_team_id=t1.id, user_id=lead.id, role="owner"))
        db.add(SubTeamMember(sub_team_id=t1.id, user_id=a1.id, role="member"))
        db.add(SubTeamMember(sub_team_id=t2.id, user_id=lead.id, role="owner"))
        db.add(SubTeamMember(sub_team_id=t2.id, user_id=b1.id, role="member"))
        await db.commit()

        a1_ids = set(await get_visible_capturer_ids(db, a1.id))
        assert a1.id in a1_ids
        assert lead.id in a1_ids
        assert b1.id not in a1_ids

        lead_ids = set(await get_visible_capturer_ids(db, lead.id))
        assert {lead.id, a1.id, b1.id} <= lead_ids
