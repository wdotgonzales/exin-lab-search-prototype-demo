"""sources, documents, jobs and audit_logs alignment

Revision ID: 8a88f2a45de6
Revises: 4b3450430ffb
Create Date: 2026-11-18

Hand-edited: actor_id is RENAMED (not dropped) so audit history survives,
the CHECK constraints are added explicitly (autogenerate can't detect them on
an existing table), and the 'Manual uploads' source row is seeded.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8a88f2a45de6"
down_revision: str | Sequence[str] | None = "4b3450430ffb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_ACTIONS = (
    "action IN ('user.login', 'user.login_failed', 'user.created', "
    "'document.upload', 'document.delete', 'document.reindex', 'source.sync')"
)


def upgrade() -> None:
    # ── sources ─────────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind IN ('upload', 's3')", name=op.f("ck_sources_kind")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_sources_created_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
    )
    op.execute("INSERT INTO sources (name, kind) VALUES ('Manual uploads', 'upload')")

    # ── documents ───────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("external_path", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("file_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("access_level", sa.Text(), server_default="general", nullable=False),
        sa.Column("document_date", sa.Date(), nullable=True),
        sa.Column("title_tsv", postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', title)", persisted=True), nullable=False),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("access_level IN ('general', 'restricted')", name=op.f("ck_documents_access_level")),
        sa.CheckConstraint("file_type IN ('pdf', 'docx', 'xlsx', 'csv', 'md', 'txt')", name=op.f("ck_documents_file_type")),
        sa.CheckConstraint("status IN ('pending', 'processing', 'indexed', 'failed')", name=op.f("ck_documents_status")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("fk_documents_source_id_sources"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name=op.f("fk_documents_uploaded_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("source_id", "external_path", name=op.f("uq_documents_source_id_external_path")),
    )
    op.create_index(op.f("idx_documents_source"), "documents", ["source_id"])
    op.create_index(op.f("idx_documents_hash"), "documents", ["source_id", "content_hash"])
    op.create_index(op.f("idx_documents_filters"), "documents", ["status", "file_type", "document_date"])
    op.create_index(op.f("idx_documents_title_tsv"), "documents", ["title_tsv"], postgresql_using="gin")

    # ── jobs ────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("job_type IN ('ingest_document', 'sync_source')", name=op.f("ck_jobs_job_type")),
        sa.CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name=op.f("ck_jobs_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("idx_jobs_queue"), "jobs", ["run_after"], postgresql_where=sa.text("status = 'queued'"))

    # ── audit_logs: align with the Technical Design ─────────
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")

    # Rename keeps the data (autogenerate wanted drop + add, which would lose it).
    op.drop_constraint(op.f("fk_audit_logs_actor_id_users"), "audit_logs", type_="foreignkey")
    op.alter_column("audit_logs", "actor_id", new_column_name="actor_user_id")
    op.create_foreign_key(
        op.f("fk_audit_logs_actor_user_id_users"), "audit_logs", "users",
        ["actor_user_id"], ["id"], ondelete="SET NULL",
    )

    op.add_column("audit_logs", sa.Column("actor_email", sa.Text(), nullable=True))
    op.add_column("audit_logs", sa.Column("target_label", sa.Text(), nullable=True))

    # Backfill the snapshots for rows written before this migration.
    op.execute(
        "UPDATE audit_logs SET actor_email = metadata->>'email', metadata = metadata - 'email' "
        "WHERE action = 'user.login_failed' AND metadata ? 'email'"
    )
    op.execute(
        "UPDATE audit_logs a SET actor_email = u.email FROM users u "
        "WHERE a.actor_user_id = u.id AND a.actor_email IS NULL"
    )
    op.execute(
        "UPDATE audit_logs SET target_label = metadata->>'email' "
        "WHERE action = 'user.created' AND target_label IS NULL"
    )

    op.create_index(op.f("idx_audit_logs_created"), "audit_logs", ["created_at"])
    op.create_index(op.f("idx_audit_logs_actor"), "audit_logs", ["actor_user_id", "created_at"])
    op.create_index(op.f("idx_audit_logs_target"), "audit_logs", ["target_type", "target_id"])
    op.create_check_constraint(op.f("ck_audit_logs_action"), "audit_logs", AUDIT_ACTIONS)
    op.create_check_constraint(
        op.f("ck_audit_logs_target_type"), "audit_logs", "target_type IN ('user', 'document', 'source')"
    )


def downgrade() -> None:
    # ── audit_logs back to the Auth shape ───────────────────
    op.drop_constraint(op.f("ck_audit_logs_target_type"), "audit_logs", type_="check")
    op.drop_constraint(op.f("ck_audit_logs_action"), "audit_logs", type_="check")
    op.drop_index(op.f("idx_audit_logs_target"), table_name="audit_logs")
    op.drop_index(op.f("idx_audit_logs_actor"), table_name="audit_logs")
    op.drop_index(op.f("idx_audit_logs_created"), table_name="audit_logs")

    op.execute(
        "UPDATE audit_logs SET metadata = metadata || jsonb_build_object('email', actor_email) "
        "WHERE action = 'user.login_failed' AND actor_email IS NOT NULL"
    )
    op.drop_column("audit_logs", "target_label")
    op.drop_column("audit_logs", "actor_email")

    op.drop_constraint(op.f("fk_audit_logs_actor_user_id_users"), "audit_logs", type_="foreignkey")
    op.alter_column("audit_logs", "actor_user_id", new_column_name="actor_id")
    op.create_foreign_key(
        op.f("fk_audit_logs_actor_id_users"), "audit_logs", "users",
        ["actor_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"])
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])

    # ── new tables, children first ──────────────────────────
    op.drop_index(op.f("idx_jobs_queue"), table_name="jobs", postgresql_where=sa.text("status = 'queued'"))
    op.drop_table("jobs")
    op.drop_index(op.f("idx_documents_title_tsv"), table_name="documents", postgresql_using="gin")
    op.drop_index(op.f("idx_documents_filters"), table_name="documents")
    op.drop_index(op.f("idx_documents_hash"), table_name="documents")
    op.drop_index(op.f("idx_documents_source"), table_name="documents")
    op.drop_table("documents")
    op.drop_table("sources")
