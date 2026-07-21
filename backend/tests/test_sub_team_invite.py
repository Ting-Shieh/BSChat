"""Sub-team email invite + F1 notifications."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.db import async_session_factory
from app.models.notification import UserNotification
from app.models.organization import Organization, OrgMember
from app.models.sub_team import SubTeam, SubTeamMember
from app.models.team_invite import TeamInvite
from app.models.user import User, Workspace
from app.modules.sub_team import service as sub_team_service


async def _mk_user(db, email: str | None = None) -> User:
    user = User(
        email=email or f"st-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Member",
    )
    db.add(user)
    await db.flush()
    db.add(Workspace(owner_user_id=user.id, name="Personal"))
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_owner_invite_creates_notification_and_pending():
    async with async_session_factory() as db:
        owner = await _mk_user(db, "owner-invite@example.com")
        peer = await _mk_user(db, "peer-invite@example.com")
        outsider = await _mk_user(db, "outsider@example.com")
        org = Organization(
            name="EntInv",
            slug=f"ent-inv-{uuid.uuid4().hex[:8]}",
            is_enterprise=True,
            primary_admin_user_id=owner.id,
        )
        db.add(org)
        await db.flush()
        db.add(OrgMember(org_id=org.id, user_id=owner.id, role="admin"))
        db.add(OrgMember(org_id=org.id, user_id=peer.id, role="member"))
        # outsider is NOT org member
        team = SubTeam(org_id=org.id, name="業務一組", created_by_user_id=owner.id)
        db.add(team)
        await db.flush()
        db.add(SubTeamMember(sub_team_id=team.id, user_id=owner.id, role="owner"))
        await db.commit()

        # reload users in session
        owner = (await db.execute(select(User).where(User.id == owner.id))).scalar_one()
        peer = (await db.execute(select(User).where(User.id == peer.id))).scalar_one()
        outsider = (
            await db.execute(select(User).where(User.id == outsider.id))
        ).scalar_one()
        team = (await db.execute(select(SubTeam).where(SubTeam.id == team.id))).scalar_one()

        with pytest.raises(Exception) as ei:
            await sub_team_service.create_sub_team_invite(
                db, owner, team_id=team.id, invited_email=outsider.email
            )
        assert "NOT_ORG_MEMBER" in str(ei.value)

        invite, raw, *_ = await sub_team_service.create_sub_team_invite(
            db, owner, team_id=team.id, invited_email=peer.email
        )
        await db.commit()
        assert invite.invited_email == peer.email
        assert invite.max_uses == 1
        assert sub_team_service.invite_status(invite) == "pending"
        assert raw

        notifs = (
            await db.execute(
                select(UserNotification).where(UserNotification.user_id == peer.id)
            )
        ).scalars().all()
        assert len(notifs) == 1
        assert notifs[0].kind == "sub_team_invite"
        assert notifs[0].payload["invite_id"] == str(invite.id)

        joined = await sub_team_service.accept_sub_team_invite_by_id(db, peer, invite.id)
        await db.commit()
        assert joined.id == team.id
        invite2 = (
            await db.execute(select(TeamInvite).where(TeamInvite.id == invite.id))
        ).scalar_one()
        assert sub_team_service.invite_status(invite2) == "accepted"


@pytest.mark.asyncio
async def test_member_cannot_invite():
    async with async_session_factory() as db:
        owner = await _mk_user(db)
        member = await _mk_user(db)
        peer = await _mk_user(db)
        org = Organization(
            name="Ent2",
            slug=f"ent2-{uuid.uuid4().hex[:8]}",
            is_enterprise=True,
            primary_admin_user_id=owner.id,
        )
        db.add(org)
        await db.flush()
        for u, role in ((owner, "admin"), (member, "member"), (peer, "member")):
            db.add(OrgMember(org_id=org.id, user_id=u.id, role=role))
        team = SubTeam(org_id=org.id, name="T", created_by_user_id=owner.id)
        db.add(team)
        await db.flush()
        db.add(SubTeamMember(sub_team_id=team.id, user_id=owner.id, role="owner"))
        db.add(SubTeamMember(sub_team_id=team.id, user_id=member.id, role="member"))
        await db.commit()

        member = (await db.execute(select(User).where(User.id == member.id))).scalar_one()
        peer = (await db.execute(select(User).where(User.id == peer.id))).scalar_one()
        team = (await db.execute(select(SubTeam).where(SubTeam.id == team.id))).scalar_one()

        with pytest.raises(Exception) as ei:
            await sub_team_service.create_sub_team_invite(
                db, member, team_id=team.id, invited_email=peer.email
            )
        assert "NOT_OWNER" in str(ei.value)


@pytest.mark.asyncio
async def test_invite_status_revoked_expired():
    async with async_session_factory() as db:
        owner = await _mk_user(db)
        org = Organization(
            name="Ent3",
            slug=f"ent3-{uuid.uuid4().hex[:8]}",
            is_enterprise=True,
            primary_admin_user_id=owner.id,
        )
        db.add(org)
        await db.flush()
        invite = TeamInvite(
            org_id=org.id,
            token_hash="x" * 64,
            created_by_user_id=owner.id,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            max_uses=1,
            use_count=0,
            invite_kind="sub_team",
            invited_email="a@b.com",
        )
        assert sub_team_service.invite_status(invite) == "expired"
        invite.expires_at = datetime.now(UTC) + timedelta(days=1)
        invite.revoked_at = datetime.now(UTC)
        assert sub_team_service.invite_status(invite) == "revoked"
