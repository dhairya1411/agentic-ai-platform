# Phase 12 — Testing and Quality

## Objective

Establish demonstration-ready quality gates across API contracts, security primitives, agent behavior, workflow policy, memory authorization, and frontend compilation.

## Test strategy

- Unit tests cover JWT/credential cryptography, webhook signatures, workflow policy, memory access containment, and structured model-output validation.
- Graph tests use deterministic fake services to verify specialist routing, confidence gating, and bounded retries without provider calls.
- API contract tests use FastAPI's test client and no live database or connector credentials.
- Frontend quality uses TypeScript checks and a production Next.js build; demo data keeps the UI tests deterministic.

## Quality gates

```powershell
# API
uv run ruff check .
uv run mypy src
uv run pytest

# Web
npm run typecheck
npm run build
```

## Next steps

Added dashboard contract coverage to the existing security, graph, webhook, workflow-policy, and memory-authorization test suite. Phase 13 hardens images, Compose deployment, monitoring, alerting, and release workflow.
