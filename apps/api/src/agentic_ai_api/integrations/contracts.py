"""Provider-neutral contracts for deduplicated ingress and safe mutations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceEventEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider: Literal["slack", "github", "jira"]
    provider_event_id: str = Field(min_length=1, max_length=255)
    payload: dict[str, Any]


class JiraMutation(BaseModel):
    model_config = ConfigDict(frozen=True)
    issue_key: str = Field(pattern=r"^[A-Z][A-Z0-9]+-\d+$")
    transition_id: str
    idempotency_key: str = Field(min_length=16, max_length=255)
