"""document summaries and agent logging

Revision ID: e5f3c9d2a1b6
Revises: d4e2b8c1a9f5
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5f3c9d2a1b6"
down_revision: str | None = "d4e2b8c1a9f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "ai_queries",
        sa.Column(
            "tool_calls",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "ai_queries",
        sa.Column(
            "general_knowledge",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_queries", "general_knowledge")
    op.drop_column("ai_queries", "tool_calls")
    op.drop_column("documents", "summary")
