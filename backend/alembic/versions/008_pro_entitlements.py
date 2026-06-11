"""Add Pro entitlement fields: M3.5 person enrich quota + settings."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_pro_entitlements"
down_revision: Union[str, None] = "007_review_deferred"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_entitlements",
        sa.Column(
            "person_enrich_mode",
            sa.String(length=20),
            nullable=False,
            server_default="inference_only",
        ),
    )
    op.add_column(
        "user_entitlements",
        sa.Column(
            "person_linkedin_quota_monthly",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user_entitlements",
        sa.Column(
            "person_linkedin_used_this_month",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "user_entitlements",
        sa.Column("person_linkedin_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_entitlements",
        sa.Column(
            "person_linkedin_auto_on_url",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_entitlements", "person_linkedin_auto_on_url")
    op.drop_column("user_entitlements", "person_linkedin_reset_at")
    op.drop_column("user_entitlements", "person_linkedin_used_this_month")
    op.drop_column("user_entitlements", "person_linkedin_quota_monthly")
    op.drop_column("user_entitlements", "person_enrich_mode")
