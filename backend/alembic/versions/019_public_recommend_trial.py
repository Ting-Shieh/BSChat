"""Add public recommend lifetime trial fields on user_entitlements."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019_public_recommend_trial"
down_revision: Union[str, None] = "018_self_hosted_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_entitlements",
        sa.Column(
            "public_recommend_lifetime_quota",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
    )
    op.add_column(
        "user_entitlements",
        sa.Column(
            "public_recommend_used_lifetime",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("user_entitlements", "public_recommend_used_lifetime")
    op.drop_column("user_entitlements", "public_recommend_lifetime_quota")
