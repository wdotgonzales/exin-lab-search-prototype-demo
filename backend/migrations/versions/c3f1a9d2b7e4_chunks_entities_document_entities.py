"""chunks, entities, document_entities

Revision ID: c3f1a9d2b7e4
Revises: 8a88f2a45de6
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "c3f1a9d2b7e4"
down_revision: str | None = "8a88f2a45de6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "chunks",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', content)", persisted=True),
            nullable=True,
        ),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_id_chunk_index"),
    )
    op.create_index(
        "idx_chunks_search_vector", "chunks", ["search_vector"], postgresql_using="gin"
    )
    op.create_index(
        "idx_chunks_embedding",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "entity_type IN ('mouse','virus_batch','experiment','cohort')",
            name="ck_entities_entity_type",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_entities"),
        sa.UniqueConstraint("code", name="uq_entities_code"),
    )

    op.create_table(
        "document_entities",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "mention_count", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_entities_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["entities.id"],
            name="fk_document_entities_entity_id_entities",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("document_id", "entity_id", name="pk_document_entities"),
    )
    op.create_index("idx_doc_entities_entity", "document_entities", ["entity_id"])


def downgrade() -> None:
    op.drop_index("idx_doc_entities_entity", table_name="document_entities")
    op.drop_table("document_entities")
    op.drop_table("entities")
    op.drop_index("idx_chunks_embedding", table_name="chunks")
    op.drop_index("idx_chunks_search_vector", table_name="chunks")
    op.drop_table("chunks")
    # The vector extension is left installed on purpose: dropping it is harmless to skip
    # and it may be shared.
