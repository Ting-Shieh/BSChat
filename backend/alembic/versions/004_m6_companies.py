"""M6 companies and enrichment tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_m6"
down_revision: Union[str, None] = "003_m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=512), nullable=True),
        sa.Column("enrich_status", sa.String(length=20), server_default="never", nullable=False),
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enrich_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("needs_review", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "normalized_name", name="uq_companies_user_normalized"),
    )
    op.create_index("idx_companies_user_status", "companies", ["user_id", "enrich_status"])

    op.create_table(
        "company_enrichments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrich_version", sa.Integer(), nullable=False),
        sa.Column("main_products", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("industry_tags", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("fields_provenance", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("overall_confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("model", sa.String(length=50), nullable=True),
        sa.Column("prompt_version", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("candidate_companies", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "enrich_version", name="uq_company_enrich_version"),
    )
    op.create_index(
        "idx_enrichments_company_latest",
        "company_enrichments",
        ["company_id", "enrich_version"],
    )

    op.create_table(
        "company_field_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(length=50), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False),
        sa.Column("override_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "user_id", "field_name", name="uq_company_field_review"),
    )

    op.create_table(
        "enrich_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="requested", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_enrich_jobs_idempotency"),
    )
    op.create_index("idx_enrich_jobs_company_created", "enrich_jobs", ["company_id", "created_at"])

    op.create_foreign_key(
        "fk_contacts_company_id",
        "contacts",
        "companies",
        ["company_id"],
        ["id"],
    )

    op.add_column(
        "user_entitlements",
        sa.Column("daily_enrich_quota", sa.Integer(), server_default="50", nullable=False),
    )
    op.add_column(
        "user_entitlements",
        sa.Column("daily_enrich_used", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "user_entitlements",
        sa.Column("daily_enrich_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_entitlements",
        sa.Column("manual_refresh_reset_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_entitlements", "manual_refresh_reset_at")
    op.drop_column("user_entitlements", "daily_enrich_reset_at")
    op.drop_column("user_entitlements", "daily_enrich_used")
    op.drop_column("user_entitlements", "daily_enrich_quota")
    op.drop_constraint("fk_contacts_company_id", "contacts", type_="foreignkey")
    op.drop_index("idx_enrich_jobs_company_created", table_name="enrich_jobs")
    op.drop_table("enrich_jobs")
    op.drop_table("company_field_reviews")
    op.drop_index("idx_enrichments_company_latest", table_name="company_enrichments")
    op.drop_table("company_enrichments")
    op.drop_index("idx_companies_user_status", table_name="companies")
    op.drop_table("companies")
