"""Dashboard API contract tests."""

from fastapi.testclient import TestClient

from agentic_ai_api.core.config import Settings
from agentic_ai_api.main import create_app


def test_dashboard_summary_has_stable_empty_state_contract() -> None:
    app = create_app(Settings(database_enabled=False))
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    assert response.json() == {
        "sprint_progress": None,
        "project_health": "unknown",
        "open_blockers": 0,
        "recent_actions": [],
    }
