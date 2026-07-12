"""Health endpoint and HTTP-boundary tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_liveness_returns_correlated_response(client: TestClient) -> None:
    """Liveness reports process health and preserves an inbound request ID."""
    response = client.get("/api/v1/health/live", headers={"X-Request-ID": "request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"
    assert response.json() == {
        "status": "ok",
        "service": "Agentic AI Platform Test",
        "checks": {"application": "ok"},
    }


def test_readiness_returns_verified_current_checks(client: TestClient) -> None:
    """Readiness exposes only dependencies that are currently implemented."""
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"] == {"application": "ok", "database": "disabled"}


def test_unknown_route_uses_fastapi_not_found_response(client: TestClient) -> None:
    """Routing preserves FastAPI's normal 404 semantics."""
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
