# Phase 14 — Documentation

## Objective

Complete the portfolio documentation package for developers, reviewers, and operators.

## Documentation set

- `README.md`: product summary, phase status, and quick links.
- `docs/architecture/`: architecture decisions and one document per delivery phase.
- `docs/api/api-specification.md`: REST conventions and workflow API design.
- `docs/operations/local-development.md`: local services and observability endpoints.
- `.env.example`: complete local configuration reference without secrets.

## Demo walkthrough

1. Start Compose services and open the dashboard at `http://localhost:3000`.
2. Review project progress, agent activity, governed memory, and settings.
3. Open Approvals and use the demo approve/reject controls.
4. Inspect API health at `http://localhost:8000/api/v1/health/live` and OpenAPI at `/api/v1/docs`.
5. Explain the progression from verified webhooks, through LangGraph analysis and memory retrieval, to policy-gated execution.

## Production note

The frontend is deliberately in portfolio-demo mode with local data. Production deployment requires the documented tenant-scoped repository endpoints, real OAuth credentials, durable LangGraph checkpointing, and live connector contract tests.
