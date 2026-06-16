"""M11 public directory — organizations, stubs, Pool B index."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_m11_public_directory"
down_revision: Union[str, None] = "010_query_augmentations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "org_members",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), server_default="admin", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("org_id", "user_id"),
    )
    op.create_index("idx_org_members_user", "org_members", ["user_id"])

    op.create_table(
        "public_business_stubs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "responsibility_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "product_keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("external_card_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unpublished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('draft','published','unpublished')",
            name="chk_stub_status",
        ),
    )
    op.create_index("idx_stubs_org", "public_business_stubs", ["org_id"])
    op.create_index("idx_stubs_org_status", "public_business_stubs", ["org_id", "status"])

    op.create_table(
        "public_directory_documents",
        sa.Column("stub_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["stub_id"], ["public_business_stubs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("stub_id"),
    )
    op.create_index("idx_pdd_org", "public_directory_documents", ["org_id"])
    op.execute(
        "CREATE INDEX idx_pdd_search_vector ON public_directory_documents USING GIN (search_vector)"
    )
    op.execute(
        "CREATE INDEX idx_pdd_search_text_trgm ON public_directory_documents USING GIN (search_text gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pdd_search_text_trgm")
    op.execute("DROP INDEX IF EXISTS idx_pdd_search_vector")
    op.drop_index("idx_pdd_org", table_name="public_directory_documents")
    op.drop_table("public_directory_documents")
    op.drop_index("idx_stubs_org_status", table_name="public_business_stubs")
    op.drop_index("idx_stubs_org", table_name="public_business_stubs")
    op.drop_table("public_business_stubs")
    op.drop_index("idx_org_members_user", table_name="org_members")
    op.drop_table("org_members")
    op.drop_index("idx_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
