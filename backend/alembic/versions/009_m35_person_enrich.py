"""M3.5 person enrichment: person_enrichments, person_enrich_jobs + contact columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_m35_person_enrich"
down_revision: Union[str, None] = "008_pro_entitlements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "person_enrichments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enrich_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("profile_headline", sa.Text(), nullable=True),
        sa.Column("profile_summary", sa.Text(), nullable=True),
        sa.Column("person_scope", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("match_inputs", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.String(length=50), nullable=True),
        sa.Column("prompt_version", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_person_enrich_contact_active",
        "person_enrichments",
        ["contact_id"],
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "person_enrich_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("candidates", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), unique=True, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_person_enrich_jobs_contact", "person_enrich_jobs", ["contact_id"])

    op.add_column("contacts", sa.Column("linkedin_url", sa.Text(), nullable=True))
    op.add_column("contacts", sa.Column("person_scope", sa.Text(), nullable=True))
    op.add_column("contacts", sa.Column("person_scope_confidence", sa.Float(), nullable=True))
    op.add_column("contacts", sa.Column("person_enrich_status", sa.String(length=20), nullable=True))
    op.add_column("contacts", sa.Column("person_enriched_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("contacts", "person_enriched_at")
    op.drop_column("contacts", "person_enrich_status")
    op.drop_column("contacts", "person_scope_confidence")
    op.drop_column("contacts", "person_scope")
    op.drop_column("contacts", "linkedin_url")
    op.drop_index("idx_person_enrich_jobs_contact", table_name="person_enrich_jobs")
    op.drop_table("person_enrich_jobs")
    op.drop_index("idx_person_enrich_contact_active", table_name="person_enrichments")
    op.drop_table("person_enrichments")
