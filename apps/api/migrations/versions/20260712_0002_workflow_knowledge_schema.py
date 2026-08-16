"""Add workflow, collaboration, and knowledge records.

Revision ID: 20260712_0002
Revises: 20260712_0001
Create Date: 2026-07-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260712_0002"
down_revision: str | None = "20260712_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tenant_table(name: str, *columns: sa.Column[object], constraints: tuple[object, ...] = ()) -> None:
    op.create_table(
        name,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        *columns,
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *constraints,
    )
    expression = "organization_id = NULLIF(current_setting('app.current_organization_id', true), '')::uuid"
    op.execute(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {name} FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_isolation ON {name} USING ({expression}) WITH CHECK ({expression})")


def upgrade() -> None:
    json = postgresql.JSONB(astext_type=sa.Text())
    uuid = postgresql.UUID(as_uuid=True)

    _tenant_table(
        "teams",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("external_ref", sa.String(255)),
        constraints=(sa.UniqueConstraint("organization_id", "name", name="uq_team_organization_name"),),
    )
    _tenant_table(
        "team_memberships",
        sa.Column("team_id", uuid, sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("membership_id", uuid, sa.ForeignKey("organization_memberships.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        constraints=(sa.UniqueConstraint("team_id", "membership_id", name="uq_team_membership"),),
    )
    _tenant_table(
        "sprints",
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("external_ref", sa.String(255)),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )
    _tenant_table(
        "work_items",
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_ref", sa.String(255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("assignee_membership_id", uuid, sa.ForeignKey("organization_memberships.id")),
        constraints=(
            sa.UniqueConstraint("organization_id", "provider", "external_ref", name="uq_work_item_provider_ref"),
        ),
    )
    _tenant_table(
        "conversations",
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_ref", sa.String(255), nullable=False),
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id")),
        constraints=(
            sa.UniqueConstraint(
                "organization_id", "provider", "external_ref", name="uq_conversation_provider_ref"
            ),
        ),
    )
    _tenant_table(
        "messages",
        sa.Column("conversation_id", uuid, sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("author_user_id", uuid, sa.ForeignKey("users.id")),
        sa.Column("provider_ref", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        constraints=(sa.UniqueConstraint("organization_id", "provider_ref", name="uq_message_provider_ref"),),
    )
    _tenant_table(
        "meetings",
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id")),
        sa.Column("external_ref", sa.String(255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transcript_ref", sa.String(500)),
        constraints=(sa.UniqueConstraint("organization_id", "external_ref", name="uq_meeting_external_ref"),),
    )
    _tenant_table(
        "workflow_definitions",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("graph_json", json, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        constraints=(sa.UniqueConstraint("organization_id", "name", "version", name="uq_workflow_name_version"),),
    )
    _tenant_table(
        "workflow_runs",
        sa.Column("workflow_definition_id", uuid, sa.ForeignKey("workflow_definitions.id"), nullable=False),
        sa.Column("source_event_id", uuid, sa.ForeignKey("source_events.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("checkpoint_ref", sa.String(500)),
        sa.Column("trace_id", sa.String(64), nullable=False),
    )
    _tenant_table(
        "action_proposals",
        sa.Column("workflow_run_id", uuid, sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("action_type", sa.String(120), nullable=False),
        sa.Column("arguments_json", json, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("risk_level", sa.String(32), nullable=False),
    )
    _tenant_table(
        "approvals",
        sa.Column("action_proposal_id", uuid, sa.ForeignKey("action_proposals.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("decided_by", uuid, sa.ForeignKey("users.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.Text()),
    )
    _tenant_table(
        "executed_actions",
        sa.Column("proposal_id", uuid, sa.ForeignKey("action_proposals.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("request_json", json, nullable=False),
        sa.Column("result_json", json),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )
    _tenant_table(
        "notifications",
        sa.Column("executed_action_id", uuid, sa.ForeignKey("executed_actions.id")),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("recipient_ref", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
    )
    _tenant_table(
        "oauth_connections",
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("encrypted_credentials", sa.LargeBinary(), nullable=False),
        sa.Column("scopes", json, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        constraints=(sa.UniqueConstraint("organization_id", "provider", name="uq_oauth_provider"),),
    )
    _tenant_table(
        "api_keys",
        sa.Column("key_prefix", sa.String(24), nullable=False),
        sa.Column("secret_hash", sa.String(255), nullable=False),
        sa.Column("scopes", json, nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        constraints=(sa.UniqueConstraint("organization_id", "key_prefix", name="uq_api_key_prefix"),),
    )
    _tenant_table(
        "knowledge_sources",
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_ref", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("access_policy_json", json, nullable=False),
        constraints=(
            sa.UniqueConstraint("organization_id", "provider", "external_ref", name="uq_knowledge_provider_ref"),
        ),
    )
    _tenant_table(
        "memories",
        sa.Column("project_id", uuid, sa.ForeignKey("projects.id")),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.Numeric(5, 4), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("qdrant_point_id", uuid, unique=True),
    )
    _tenant_table(
        "prompt_templates",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column("output_schema_json", json, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        constraints=(sa.UniqueConstraint("organization_id", "name", "version", name="uq_prompt_name_version"),),
    )
    _tenant_table(
        "dead_letter_events",
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("payload_json", json, nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=False),
    )

    for table_name in ["work_items", "workflow_runs", "action_proposals", "executed_actions", "memories"]:
        op.create_index(f"ix_{table_name}_organization_created", table_name, ["organization_id", "created_at"])


def downgrade() -> None:
    for table_name in [
        "dead_letter_events", "prompt_templates", "memories", "knowledge_sources", "api_keys", "oauth_connections",
        "notifications", "executed_actions", "approvals", "action_proposals", "workflow_runs", "workflow_definitions",
        "meetings", "messages", "conversations", "work_items", "sprints", "team_memberships", "teams",
    ]:
        op.drop_table(table_name)
