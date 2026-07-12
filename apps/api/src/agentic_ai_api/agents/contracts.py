"""Typed planning and proposal contracts shared by LangGraph nodes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SpecialistName = Literal[
    "slack", "github", "jira", "meeting", "standup", "reporting", "notification", "knowledge"
]
RiskLevel = Literal["low", "medium", "high"]


class PlanOutput(BaseModel):
    """A bounded, ordered plan emitted by the planner model."""

    model_config = ConfigDict(frozen=True)
    objective: str = Field(min_length=1, max_length=2_000)
    specialists: list[SpecialistName] = Field(default_factory=list, max_length=8)
    confidence: float = Field(ge=0.0, le=1.0)


class ActionProposal(BaseModel):
    """A policy-gated candidate action; this contract never invokes a tool."""

    model_config = ConfigDict(frozen=True)
    action_type: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,119}$")
    arguments: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    rationale: str = Field(min_length=1, max_length=4_000)


class SpecialistOutput(BaseModel):
    """Structured result from a specialist node."""

    model_config = ConfigDict(frozen=True)
    summary: str = Field(min_length=1, max_length=4_000)
    proposals: list[ActionProposal] = Field(default_factory=list, max_length=20)
    confidence: float = Field(ge=0.0, le=1.0)


class ConfidenceDecision(BaseModel):
    """Policy result persisted with every proposed action."""

    model_config = ConfigDict(frozen=True)
    action_type: str
    approval_required: bool
    reason: str
