# Phase 2 — Project Setup

## Objective

Create a reproducible, secure development foundation for the platform before product behavior is implemented. The setup separates API, worker, and web runtimes while making infrastructure services available locally through Docker Compose.

## Architecture

- The API and worker are separate Python 3.12 packages so their dependency and scaling profiles can diverge without forcing a premature microservice split.
- The web package is a Node.js 22/TypeScript boundary, ready for the Next.js application planned in Phase 11.
- PostgreSQL, Redis, RabbitMQ, Qdrant, Jaeger, Prometheus, and Grafana run as pinned local containers with health checks and named volumes.
- CI validates Python style, typing, package smoke tests, TypeScript configuration, and Docker Compose syntax. Product build gates begin once the relevant application code exists.

## Folder structure

```text
apps/api/                    # Python API runtime contract and quality configuration
apps/worker/                 # Python background-worker runtime contract
apps/web/                    # Node/TypeScript frontend runtime contract
deploy/monitoring/           # Prometheus and Grafana provisioning
.github/workflows/           # CI quality and Compose validation
docs/operations/             # Local-development runbook
compose.yaml                 # Local infrastructure topology
.env.example                 # Safe environment-variable template
```

## Design explanation

Pinned container tags make local behavior reproducible. Named volumes preserve developer state across restarts. Only local-development ports are exposed, and `.env` remains untracked. The supplied credentials are deliberately invalid for production and must be replaced through a secret manager when deployment work begins.

`uv` is selected for Python dependency synchronization because it creates deterministic project environments and has first-class CI support. Frontend dependency locking will be added with the first Next.js implementation, avoiding a generated lockfile whose content cannot be verified in this environment.

## Implementation

- Added root ignore rules, environment template, npm workspace metadata, and a project README.
- Added Dockerfiles for isolated, non-root API/worker/web production runtimes.
- Added Python packaging, Ruff, mypy, and pytest configuration plus package smoke tests.
- Added strict TypeScript compiler configuration.
- Added Docker Compose services and monitoring datasource/configuration.
- Added GitHub Actions quality and Compose validation jobs.

## Testing

Static validation completed for the created file tree and configuration references. Docker, Python, Node.js, npm, and uv are unavailable in the current environment, so container startup and language-tool execution could not be run here. The exact validation commands are documented in the local-development guide and included in CI.

## Documentation

See [local development](../operations/local-development.md) for prerequisites, startup commands, endpoints, security notes, and verification steps.

## Next steps

Begin Phase 3: compose the FastAPI application, implement configuration loading, request IDs, structured errors, health/readiness endpoints, dependency injection, and the initial API test harness.
