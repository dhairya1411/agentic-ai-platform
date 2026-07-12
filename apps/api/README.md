# API service

Phase 3 establishes the FastAPI composition root and HTTP boundary. Run locally with:

```powershell
uv sync --all-groups
uv run uvicorn agentic_ai_api.main:app --reload --host 0.0.0.0 --port 8000
```

The endpoints currently implemented are `GET /api/v1/health/live` and `GET /api/v1/health/ready`. Every successful request receives an `X-Request-ID` response header. Expected API errors use the documented `{ "error": { ... } }` envelope.
