# Data Model and Database Schema

## Modeling rules

- PostgreSQL is the authoritative store. Qdrant stores only vector indexes plus references to authoritative memory records.
- All tenant-owned tables include `organization_id`, immutable `id` (UUIDv7), `created_at`, and `updated_at` unless the table is append-only.
- Connector payloads are retained in a protected JSONB envelope with a content hash; normalized fields are queried through explicit columns.
- Mutating workflow records carry `idempotency_key`; external action records also store the provider-side resource/version used for verification.

## Core tenancy and identity

| Table | Key columns | Purpose |
| --- | --- | --- |
| `organizations` | `id`, `name`, `slug`, `plan`, `settings_json` | Tenant boundary and subscription/configuration root. |
| `users` | `id`, `email`, `display_name`, `status` | Global authenticated identity. |
| `organization_memberships` | `organization_id`, `user_id`, `role`, `permissions_json` | Tenant membership and RBAC. |
| `teams` | `organization_id`, `name`, `external_ref` | Product/engineering teams. |
| `team_memberships` | `team_id`, `membership_id`, `role` | Team-specific membership. |
| `oauth_connections` | `organization_id`, `provider`, `encrypted_credentials`, `scopes`, `expires_at` | Encrypted tenant connector grant. |
| `api_keys` | `organization_id`, `key_prefix`, `secret_hash`, `scopes`, `revoked_at` | Service/API authentication. |

## Work management and ingested evidence

| Table | Key columns | Purpose |
| --- | --- | --- |
| `projects` | `organization_id`, `team_id`, `name`, `key`, `status` | Project scope and workflow defaults. |
| `sprints` | `organization_id`, `project_id`, `external_ref`, `starts_at`, `ends_at`, `status` | Sprint time boundary. |
| `work_items` | `organization_id`, `project_id`, `provider`, `external_ref`, `title`, `status`, `assignee_membership_id` | Canonical task/Jira ticket mirror. |
| `source_events` | `organization_id`, `provider`, `provider_event_id`, `payload_hash`, `occurred_at`, `received_at` | Deduplicated ingress record; unique on provider/event ID per tenant. |
| `conversations` | `organization_id`, `provider`, `external_ref`, `project_id` | Slack/email discussion container. |
| `messages` | `organization_id`, `conversation_id`, `author_user_id`, `provider_ref`, `body`, `sent_at` | Normalized messages with source linkage. |
| `pull_requests` | `organization_id`, `repository_id`, `external_ref`, `work_item_id`, `state`, `merged_at` | Delivery evidence. |
| `meetings` | `organization_id`, `project_id`, `external_ref`, `started_at`, `transcript_ref` | Meeting metadata and protected transcript location. |

## Automation, governance, and observability

| Table | Key columns | Purpose |
| --- | --- | --- |
| `workflow_definitions` | `organization_id`, `name`, `version`, `graph_json`, `enabled` | Versioned workflow configuration. |
| `workflow_runs` | `organization_id`, `workflow_definition_id`, `source_event_id`, `status`, `checkpoint_ref`, `trace_id` | Durable LangGraph execution record. |
| `action_proposals` | `organization_id`, `workflow_run_id`, `action_type`, `arguments_json`, `confidence`, `risk_level` | Candidate action before approval/execution. |
| `approvals` | `organization_id`, `action_proposal_id`, `status`, `decided_by`, `decided_at`, `reason` | Human approval lifecycle. |
| `executed_actions` | `organization_id`, `proposal_id`, `idempotency_key`, `status`, `request_json`, `result_json`, `verified_at` | Immutable external-action audit and replay defense. |
| `notifications` | `organization_id`, `executed_action_id`, `channel`, `recipient_ref`, `status`, `delivered_at` | Notification delivery history. |
| `audit_logs` | `organization_id`, `actor_type`, `actor_id`, `event_type`, `resource_type`, `resource_id`, `metadata_json`, `trace_id` | Append-only compliance ledger. |
| `outbox_events` | `organization_id`, `topic`, `payload_json`, `published_at`, `attempts` | Transactional publication to RabbitMQ. |
| `dead_letter_events` | `organization_id`, `source`, `payload_json`, `error`, `failed_at` | Operator remediation queue. |

## Knowledge and AI configuration

| Table | Key columns | Purpose |
| --- | --- | --- |
| `knowledge_sources` | `organization_id`, `provider`, `external_ref`, `title`, `access_policy_json` | Documents eligible for retrieval. |
| `memories` | `organization_id`, `project_id`, `source_type`, `content`, `importance`, `expires_at`, `qdrant_point_id` | Curated, governable long-term memory. |
| `memory_retrieval_logs` | `organization_id`, `workflow_run_id`, `memory_id`, `rank`, `used` | Retrieval traceability and evaluation. |
| `prompt_templates` | `organization_id`, `name`, `version`, `template`, `output_schema_json`, `enabled` | Versioned and reviewable prompts. |
| `model_configurations` | `organization_id`, `purpose`, `model`, `fallback_model`, `temperature`, `limits_json` | Model routing and budget controls. |

## Essential constraints and indexes

- Unique: `organizations.slug`; `users.email`; `(organization_id, provider, provider_event_id)` in `source_events`; `(organization_id, provider, external_ref)` in mirrored external resources; `executed_actions.idempotency_key`.
- Index: `(organization_id, created_at DESC)` on operational tables; `(organization_id, project_id, status)` on work items; `(workflow_run_id, status)` on action proposals; `(organization_id, trace_id)` on audit logs.
- Use GIN indexes only for bounded JSONB filtering cases; do not replace modeled attributes with unrestricted JSONB.
- Enable RLS with an organization context set by the request/worker transaction. Background jobs must set this context explicitly.

## Qdrant collection contract

Collection `organization_memory` stores `point_id`, dense vector, optional sparse vector, and payload `{organization_id, project_id, memory_id, source_type, access_tags, created_at}`. Every retrieval filter includes `organization_id`, applicable project scope, and access tags. The referenced `memories` row remains the final authorization and content source.
