"""Tenant dashboard summary endpoint."""

from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def summary() -> dict[str, object]:
    """Return a stable empty-state contract until project data is connected."""
    return {"sprint_progress": None, "project_health": "unknown", "open_blockers": 0, "recent_actions": []}
