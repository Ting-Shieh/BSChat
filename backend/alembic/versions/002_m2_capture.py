"""M2 capture migration."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_m2"
down_revision: Union[str, None] = "001_m1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capture_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=True),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("card_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("confirmed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pending_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sessions_user_status", "capture_sessions", ["user_id", "status"])

    op.create_table(
        "raw_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capture_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capture_method", sa.String(length=20), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("image_hash", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=True),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="uploading", nullable=False),
        sa.Column("review_status", sa.String(length=20), server_default="pending_review", nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["capture_session_id"], ["capture_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_raw_cards_user_idempotency"),
    )
    op.create_index("idx_raw_cards_user_status", "raw_cards", ["user_id", "status"])
    op.create_index("idx_raw_cards_session", "raw_cards", ["capture_session_id"])

    op.create_table(
        "ocr_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine", sa.String(length=50), nullable=False),
        sa.Column("engine_version", sa.String(length=20), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("extracted_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("field_confidences", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["raw_card_id"], ["raw_cards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_card_id"),
    )

    op.create_table(
        "handoff_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), server_default="ContactUpsertRequested", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["raw_card_id"], ["raw_cards.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("handoff_events")
    op.drop_table("ocr_results")
    op.drop_index("idx_raw_cards_session", table_name="raw_cards")
    op.drop_index("idx_raw_cards_user_status", table_name="raw_cards")
    op.drop_table("raw_cards")
    op.drop_index("idx_sessions_user_status", table_name="capture_sessions")
    op.drop_table("capture_sessions")
