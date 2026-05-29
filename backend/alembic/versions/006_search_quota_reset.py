"""Add search_cache_reset_at to user_entitlements

Revision ID: 006_search_quota_reset
Revises: 005_m5_search
Create Date: 2026-05-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_search_quota_reset"
down_revision: Union[str, None] = "005_m5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_entitlements",
        sa.Column("search_cache_reset_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_entitlements", "search_cache_reset_at")
