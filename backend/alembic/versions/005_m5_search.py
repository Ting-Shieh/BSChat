"""M5 search tables + contact_search_documents."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_m5"
down_revision: Union[str, None] = "004_m6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "contact_search_documents",
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("contact_id"),
    )
    op.create_index("idx_csd_user", "contact_search_documents", ["user_id"])
    op.execute(
        "CREATE INDEX idx_csd_search_vector ON contact_search_documents USING GIN (search_vector)"
    )
    op.execute(
        "CREATE INDEX idx_csd_search_text_trgm ON contact_search_documents USING GIN (search_text gin_trgm_ops)"
    )

    op.create_table(
        "search_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("parsed_intent", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("search_scope", sa.String(length=20), server_default="private", nullable=False),
        sa.Column("retrieval_mode", sa.String(length=20), server_default="cache", nullable=False),
        sa.Column("live_augmentation_used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("result_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("degraded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("suggest_live", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_search_queries_user_created", "search_queries", ["user_id", "created_at"])

    op.create_table(
        "search_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("match_reason", sa.Text(), nullable=False),
        sa.Column("match_sources", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("live_products", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_pool", sa.String(length=30), server_default="private_rolodex", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.ForeignKeyConstraint(["query_id"], ["search_queries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query_id", "contact_id", name="uq_search_result_contact"),
    )
    op.create_index("idx_search_results_query_rank", "search_results", ["query_id", "rank"])


def downgrade() -> None:
    op.drop_index("idx_search_results_query_rank", table_name="search_results")
    op.drop_table("search_results")
    op.drop_index("idx_search_queries_user_created", table_name="search_queries")
    op.drop_table("search_queries")
    op.execute("DROP INDEX IF EXISTS idx_csd_search_text_trgm")
    op.execute("DROP INDEX IF EXISTS idx_csd_search_vector")
    op.drop_index("idx_csd_user", table_name="contact_search_documents")
    op.drop_table("contact_search_documents")
