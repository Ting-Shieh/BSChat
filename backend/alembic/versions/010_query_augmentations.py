"""query_augmentations + live_augment_reset_at

Revision ID: 010
Revises: 009
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_query_augmentations"
down_revision: Union[str, None] = "009_m35_person_enrich"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "query_augmentations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("search_queries.id"), nullable=False),
        sa.Column("live_products", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("adopted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_query_augmentations_query", "query_augmentations", ["query_id"])

    op.add_column(
        "user_entitlements",
        sa.Column("live_augment_reset_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_entitlements", "live_augment_reset_at")
    op.drop_index("idx_query_augmentations_query", table_name="query_augmentations")
    op.drop_table("query_augmentations")
