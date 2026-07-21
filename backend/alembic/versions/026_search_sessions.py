"""026 — search_sessions + search_queries.session_id (multiturn DDR-v4-17)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_search_sessions"
down_revision: Union[str, None] = "025_stub_pending_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "search_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("turn_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_search_sessions_user_updated",
        "search_sessions",
        ["user_id", "updated_at"],
    )
    op.add_column(
        "search_queries",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_search_queries_session",
        "search_queries",
        "search_sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_search_queries_session", "search_queries", ["session_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_search_queries_session", table_name="search_queries")
    op.drop_constraint("fk_search_queries_session", "search_queries", type_="foreignkey")
    op.drop_column("search_queries", "session_id")
    op.drop_index("idx_search_sessions_user_updated", table_name="search_sessions")
    op.drop_table("search_sessions")
