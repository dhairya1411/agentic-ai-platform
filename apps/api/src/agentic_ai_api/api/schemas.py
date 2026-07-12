"""Shared public HTTP response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness or readiness status response."""

    status: Literal["ok", "ready"]
    service: str
    checks: dict[str, str]
