# Delivery Roadmap

## Phase 1 — Architecture

**Objective:** Establish architecture, data model, API conventions, governance model, and delivery sequencing.

**Deliverables:** This design package, decision records, initial API contract, and acceptance criteria.

## Phase 2 — Project Setup

Initialize the monorepo, Docker Compose topology, configuration validation, linting, pre-commit checks, CI skeleton, local observability stack, and developer onboarding guide.

## Phase 3 — Backend Foundation

Implement FastAPI composition, health endpoints, middleware, typed errors, request tracing, dependency injection, and repository/application/domain boundaries.

## Phase 4 — Database

Implement Alembic migrations, tenant RLS, repositories, transactional outbox, seed fixtures, and database integration tests.

## Phase 5 — Authentication and Authorization

Implement Google OAuth/OIDC, JWT/session lifecycle, organization onboarding, RBAC, encrypted connection credentials, and audit events.

## Phase 6 — LLM Integration

Implement model gateway, prompt template versioning, strict structured-output validation, tool schemas, redaction, budgets, model fallback, and evaluations.

## Phase 7 — Agent Framework

Implement LangGraph state, planner/supervisor/specialist nodes, checkpoints, retries, confidence policy, and graph tests.

## Phase 8 — Memory

Implement memory extraction/review, Qdrant indexing, hybrid retrieval, access filtering, retention controls, and retrieval quality tests.

## Phase 9 — Tool Integrations

Ship Slack, GitHub, and Jira connectors first, including OAuth, webhook verification, rate limiting, idempotent mutations, contract tests, and source reconciliation.

## Phase 10 — Workflow Engine

Implement event routing, policy evaluation, approval interrupts, action verification, notifications, scheduled follow-ups, DLQs, and operator remediation views.

## Phase 11 — Frontend

Build login/onboarding, dashboard, project views, activity/audit logs, approvals, chat, agents, and settings. Workflow builder follows after stable workflow contracts.

## Phase 12 — Testing and Quality

Add integration, contract, end-to-end, load, security, prompt regression, and failure-recovery test suites with quality gates in CI.

## Phase 13 — Deployment

Harden production images, Compose deployment, secrets integration, migrations, backup/restore, scaling guides, Prometheus/Grafana dashboards, alerting, and release workflow.

## Phase 14 — Documentation

Complete README, setup guide, developer handbook, OpenAPI publication, connector guides, operations runbooks, threat model, and user/admin documentation.

## First vertical-slice acceptance criteria

1. A signed Slack event referencing a merged GitHub pull request is durably ingested once.
2. The graph retrieves only tenant-authorized context and creates a typed Jira-update proposal.
3. Policy either auto-permits the bounded update or pauses for an authorized manager.
4. The Jira update is idempotent, externally verified, and visible in activity/audit views with a trace ID.
5. A notification is sent only after successful verification, and all failure modes are observable and recoverable.
