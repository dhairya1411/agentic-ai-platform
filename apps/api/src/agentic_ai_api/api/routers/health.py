"""Infrastructure health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from agentic_ai_api.api.dependencies import get_app_settings, get_database
from agentic_ai_api.api.schemas import HealthResponse
from agentic_ai_api.core.config import Settings
from agentic_ai_api.core.errors import APIError
from agentic_ai_api.infrastructure.database import Database

router = APIRouter(tags=["system"])


@router.get("/health/live", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def liveness(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Confirm that the API process can serve requests."""
    return HealthResponse(status="ok", service=settings.app_name, checks={"application": "ok"})


@router.get("/health/ready", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def readiness(
    settings: Settings = Depends(get_app_settings), database: Database = Depends(get_database)
) -> HealthResponse:
    """Confirm the currently implemented application dependencies are ready.

    Cache, queue, and vector-store checks are added with their adapters in later
    phases. The database status is verified whenever it is enabled.
    """
    database_status = "disabled" if not database.enabled else "ok" if await database.healthcheck() else "failed"
    if database_status == "failed":
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="dependency_unavailable",
            message="Database dependency is unavailable.",
        )
    return HealthResponse(
        status="ready",
        service=settings.app_name,
        checks={"application": "ok", "database": database_status},
    )
