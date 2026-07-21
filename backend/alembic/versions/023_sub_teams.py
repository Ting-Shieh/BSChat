"""023 — sub-teams for enterprise contact visibility (DDR-v4-10/11)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023_sub_teams"
down_revision: Union[str, None] = "022_enterprise_tenant_b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sub_teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sub_teams_org_id", "sub_teams", ["org_id"])

    op.create_table(
        "sub_team_members",
        sa.Column("sub_team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sub_team_id"], ["sub_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sub_team_id", "user_id"),
    )
    op.create_index("ix_sub_team_members_user_id", "sub_team_members", ["user_id"])

    op.add_column(
        "team_invites",
        sa.Column("sub_team_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_team_invites_sub_team_id",
        "team_invites",
        "sub_teams",
        ["sub_team_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_team_invites_sub_team_id", "team_invites", type_="foreignkey")
    op.drop_column("team_invites", "sub_team_id")
    op.drop_index("ix_sub_team_members_user_id", table_name="sub_team_members")
    op.drop_table("sub_team_members")
    op.drop_index("ix_sub_teams_org_id", table_name="sub_teams")
    op.drop_table("sub_teams")
