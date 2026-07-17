"""022 — enterprise tenant B: org flags, applications, invite kind."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022_enterprise_tenant_b"
down_revision: Union[str, None] = "021_password_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("is_enterprise", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "organizations",
        sa.Column("primary_admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("organizations", sa.Column("seat_limit", sa.Integer(), nullable=True))
    op.add_column(
        "organizations",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_organizations_primary_admin_user_id",
        "organizations",
        "users",
        ["primary_admin_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "org_members",
        sa.Column("plan_before_enterprise", sa.String(length=10), nullable=True),
    )

    op.add_column(
        "team_invites",
        sa.Column(
            "invite_kind",
            sa.String(length=32),
            nullable=False,
            server_default="team",
        ),
    )
    op.add_column(
        "team_invites",
        sa.Column("invited_email", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "enterprise_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("applicant_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("slug_requested", sa.String(length=100), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("estimated_seats", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.Column("resulting_org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["applicant_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resulting_org_id"], ["organizations.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_enterprise_applications_applicant_user_id",
        "enterprise_applications",
        ["applicant_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_enterprise_applications_applicant_user_id", table_name="enterprise_applications")
    op.drop_table("enterprise_applications")
    op.drop_column("team_invites", "invited_email")
    op.drop_column("team_invites", "invite_kind")
    op.drop_column("org_members", "plan_before_enterprise")
    op.drop_constraint("fk_organizations_primary_admin_user_id", "organizations", type_="foreignkey")
    op.drop_column("organizations", "approved_at")
    op.drop_column("organizations", "seat_limit")
    op.drop_column("organizations", "primary_admin_user_id")
    op.drop_column("organizations", "is_enterprise")
