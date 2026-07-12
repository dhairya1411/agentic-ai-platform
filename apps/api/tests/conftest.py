"""Shared API test fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentic_ai_api.core.config import Settings
from agentic_ai_api.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create an isolated application client with deterministic test settings."""
    settings = Settings(app_env="test", app_name="Agentic AI Platform Test", database_enabled=False)
    with TestClient(create_app(settings)) as test_client:
        yield test_client
