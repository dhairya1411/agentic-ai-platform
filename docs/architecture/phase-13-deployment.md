# Phase 13 — Deployment

## Objective

Harden the portfolio deployment topology for repeatable local and production-like operation.

## Deployment design

- Docker Compose provides PostgreSQL, Redis, RabbitMQ, Qdrant, observability services, API, web, and worker runtime boundaries.
- Secrets are supplied through environment variables or a production secret manager; they are never committed to images or source control.
- Migrations run before API/worker rollout. Health checks gate dependent services.
- Prometheus, Grafana, Jaeger, structured request IDs, audit logs, and dead-letter records provide operational visibility.

## Release checklist

1. Provide production secrets and `APP_ENV=production`.
2. Run database migrations.
3. Build immutable API, web, and worker images.
4. Verify API health, connector webhook signatures, queue connectivity, and Qdrant reachability.
5. Monitor workflow failures, DLQ depth, and external-action verification rates.

## Code implementation

Compose now builds API and web services, gates them on infrastructure health, exposes API/web ports, and supplies the frontend API base URL. Application images already run as non-root users.

## Next steps

Phase 14 completes developer, operator, API, and architecture documentation.
