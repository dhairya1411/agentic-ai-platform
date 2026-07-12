# Agentic AI Platform

Enterprise AI workflow automation for software-project management. The platform ingests collaboration and delivery signals, coordinates specialist agents through governed LangGraph workflows, and executes auditable actions in systems such as Jira and Slack.

## Current delivery phase

Phase 14 has begun: final developer, operator, API, architecture, and portfolio-demo documentation is being consolidated.

## Documents

- `docs/architecture/phase-1-architecture.md`
- `docs/architecture/database-schema.md`
- `docs/api/api-specification.md`
- `docs/architecture/implementation-roadmap.md`
- `docs/architecture/phase-2-project-setup.md`
- `docs/architecture/phase-3-backend-foundation.md`
- `docs/architecture/phase-4-database.md`
- `docs/architecture/phase-5-authentication.md`
- `docs/architecture/phase-6-llm-integration.md`
- `docs/architecture/phase-7-agent-framework.md`
- `docs/architecture/phase-8-memory.md`
- `docs/architecture/phase-9-tool-integrations.md`
- `docs/architecture/phase-10-workflow-engine.md`
- `docs/architecture/phase-12-testing-quality.md`
- `docs/operations/local-development.md`

## Quick start

Copy `.env.example` to `.env`, then run `docker compose up -d postgres redis rabbitmq qdrant jaeger prometheus grafana`. See the local development guide for prerequisites, validation, and endpoints.
