"""Add privacy-preserving model invocation telemetry.

Revision ID: 20260712_0004
Revises: 20260712_0003
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260712_0004"
down_revision: str | None = "20260712_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_invocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("prompt_template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prompt_templates.id")),
        sa.Column("trace_id", sa.String(64), nullable=False),
        sa.Column("provider_response_id", sa.String(255)),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    expression = "organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
    op.execute("ALTER TABLE model_invocations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE model_invocations FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_isolation ON model_invocations USING ({expression}) WITH CHECK ({expression})")
    op.create_index("ix_model_invocations_organization_created", "model_invocations", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_table("model_invocations")
