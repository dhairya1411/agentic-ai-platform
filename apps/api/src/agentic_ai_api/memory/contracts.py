"""Validated contracts for memory intake and authorized retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MemoryStatus = Literal["pending_review", "active", "rejected", "expired", "deleted"]


class MemoryCandidate(BaseModel):
    """A proposed durable fact awaiting automated or human review."""

    model_config = ConfigDict(frozen=True)
    source_type: str = Field(min_length=1, max_length=64)
    source_ref: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=20_000)
    importance: float = Field(ge=0.0, le=1.0)
    access_tags: frozenset[str] = Field(default_factory=frozenset)
    project_id: UUID | None = None
    expires_at: datetime | None = None


class MemoryHit(BaseModel):
    """An authorized result with fused semantic and lexical ranking."""

    model_config = ConfigDict(frozen=True)
    memory_id: UUID
    content: str
    source_type: str
    project_id: UUID | None
    score: float
    semantic_score: float
    lexical_score: float
