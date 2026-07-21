"""Contact pool visibility — enterprise sub-teams (DDR-v4-10/11).

V can see contacts captured by C when:
  - C == V, or
  - they share at least one sub_team membership.

Non-enterprise users (and enterprise members with no sub-team) see only themselves.
Legacy org-wide sharing is retired for enterprise tenants.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember, Organization
from app.models.sub_team import SubTeam, SubTeamMember


async def get_visible_capturer_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """User ids whose contacts the caller may list/search."""
    ent_org_ids = (
        await db.execute(
            select(Organization.id)
            .join(OrgMember, OrgMember.org_id == Organization.id)
            .where(
                OrgMember.user_id == user_id,
                Organization.is_enterprise.is_(True),
            )
        )
    ).scalars().all()
    if not ent_org_ids:
        return [user_id]

    my_team_ids = (
        await db.execute(
            select(SubTeamMember.sub_team_id)
            .join(SubTeam, SubTeam.id == SubTeamMember.sub_team_id)
            .where(
                SubTeamMember.user_id == user_id,
                SubTeam.org_id.in_(ent_org_ids),
            )
        )
    ).scalars().all()
    if not my_team_ids:
        return [user_id]

    peer_ids = (
        await db.execute(
            select(SubTeamMember.user_id).where(SubTeamMember.sub_team_id.in_(my_team_ids))
        )
    ).scalars().all()
    ids = set(peer_ids)
    ids.add(user_id)
    return list(ids)


async def get_team_user_ids(db: AsyncSession, user_id: uuid.UUID) -> list[uuid.UUID]:
    """Backward-compatible alias for get_visible_capturer_ids."""
    return await get_visible_capturer_ids(db, user_id)
