"""M3 contacts migration."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_m3"
down_revision: Union[str, None] = "002_m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("responsibility_scope", sa.Text(), nullable=True),
        sa.Column("responsibility_confidence", sa.Float(), nullable=True),
        sa.Column("phones", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("emails", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("website", sa.String(length=512), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=True),
        sa.Column("source_label", sa.String(length=255), nullable=True),
        sa.Column("capture_method", sa.String(length=20), nullable=True),
        sa.Column("review_status", sa.String(length=20), server_default="unconfirmed", nullable=False),
        sa.Column("search_status", sa.String(length=20), server_default="indexed", nullable=False),
        sa.Column("search_text", sa.Text(), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["raw_card_id"], ["raw_cards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_card_id"),
    )
    op.create_index("idx_contacts_user_updated", "contacts", ["user_id", "updated_at"])

    op.create_table(
        "contact_field_provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=50), nullable=False),
        sa.Column("current_value", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("source_ref", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id", "field_name", name="uq_contact_field"),
    )


def downgrade() -> None:
    op.drop_table("contact_field_provenance")
    op.drop_index("idx_contacts_user_updated", table_name="contacts")
    op.drop_table("contacts")
