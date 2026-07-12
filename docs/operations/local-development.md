# Local Development Guide

## Objective

Phase 2 creates a reproducible local services environment and pins language/runtime contracts. Application behavior begins in later phases.

## Prerequisites

- Docker Desktop with Docker Compose v2.
- Python 3.12 and [uv](https://docs.astral.sh/uv/) for backend/worker development.
- Node.js 22.11+ and npm 10+ for the frontend.

## Start local infrastructure

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis rabbitmq qdrant jaeger prometheus grafana
docker compose ps
```

Endpoints: PostgreSQL `localhost:5432`, Redis `localhost:6379`, RabbitMQ management `http://localhost:15672`, Qdrant `http://localhost:6333/dashboard`, Jaeger `http://localhost:16686`, Prometheus `http://localhost:9090`, and Grafana `http://localhost:3001`.

## Validate language packages

```powershell
Set-Location apps/api; uv sync --all-groups; uv run ruff check .; uv run mypy src; uv run pytest
Set-Location ../worker; uv sync --all-groups; uv run ruff check .; uv run mypy src; uv run pytest
Set-Location ../web; npm install; npm run typecheck
```

## Security notes

- `.env` is local-only and excluded from Git. Replace every example secret before shared or deployed use.
- Docker port publication is intentionally for local development. Production needs private network connectivity, a secret manager, TLS termination, and non-default credentials.
- Volumes hold local development state. Remove them only when intentionally resetting the local environment.

## Phase 2 verification

1. `docker compose config --quiet` succeeds after copying `.env.example`.
2. All infrastructure services become healthy via `docker compose ps`.
3. API/worker quality commands pass once Python and uv are installed.
4. Web type checking passes once Node and npm are installed; the production build gate begins with the Phase 11 application shell.
