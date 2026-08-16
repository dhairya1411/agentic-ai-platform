"""Add governed-memory metadata and retrieval audit records.

Revision ID: 20260712_0005
Revises: 20260712_0004
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260712_0005"
down_revision: str | None = "20260712_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "memories",
        sa.Column("source_ref", sa.String(255), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "memories",
        sa.Column("access_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )
    op.add_column(
        "memories",
        sa.Column("status", sa.String(32), nullable=False, server_default="pending_review"),
    )
    op.create_index("ix_memories_governance", "memories", ["organization_id", "status", "expires_at"])
    op.create_table(
        "memory_retrieval_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_runs.id")),
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    expression = "organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
    op.execute("ALTER TABLE memory_retrieval_logs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memory_retrieval_logs FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation ON memory_retrieval_logs "
        f"USING ({expression}) WITH CHECK ({expression})"
    )
    op.create_index("ix_memory_retrieval_logs_run", "memory_retrieval_logs", ["workflow_run_id", "rank"])


def downgrade() -> None:
    op.drop_table("memory_retrieval_logs")
    op.drop_index("ix_memories_governance", table_name="memories")
    op.drop_column("memories", "status")
    op.drop_column("memories", "access_tags")
    op.drop_column("memories", "source_ref")
