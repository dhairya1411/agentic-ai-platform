"""Graph behavior is tested with deterministic, side-effect-free agent services."""

from __future__ import annotations

from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from agentic_ai_api.agents.contracts import ActionProposal, PlanOutput, SpecialistOutput
from agentic_ai_api.agents.graph import AgentGraphFactory
from agentic_ai_api.core.config import Settings
from agentic_ai_api.llm.gateway import ModelGatewayError


class FakeServices:
    def __init__(self, plan_confidence: float = 0.95, fail_first_plan: bool = False) -> None:
        self.plan_confidence = plan_confidence
        self.fail_first_plan = fail_first_plan
        self.plan_calls = 0
        self.specialists: list[str] = []

    async def plan(self, **_: object) -> PlanOutput:
        self.plan_calls += 1
        if self.fail_first_plan and self.plan_calls == 1:
            # The real transient fault is ModelGatewayError, raised when every model
            # attempt in the gateway fails. A bare RuntimeError would not be retried.
            raise ModelGatewayError("transient model failure")
        return PlanOutput(
            objective="Triage a work update", specialists=["slack", "jira"], confidence=self.plan_confidence
        )

    async def analyze(self, **kwargs: object) -> SpecialistOutput:
        specialist = str(kwargs["specialist"])
        self.specialists.append(specialist)
        return SpecialistOutput(
            summary="Analysis complete",
            confidence=0.95,
            proposals=[
                ActionProposal(
                    action_type="jira.transition",
                    arguments={"issue_key": "ABC-1"},
                    confidence=0.95,
                    risk_level="low",
                    rationale="The source event identifies a completed backend change.",
                )
            ],
        )


@pytest.mark.asyncio
async def test_graph_runs_specialists_and_flags_proposals_for_later_policy() -> None:
    services = FakeServices()
    graph = AgentGraphFactory(Settings(), services).compile(InMemorySaver())

    result = await graph.ainvoke(
        {"organization_id": str(uuid4()), "trace_id": "trace-1", "event": {"body": "PR merged"}},
        {"configurable": {"thread_id": "workflow-1"}},
    )

    assert services.specialists == ["slack", "jira"]
    assert result["status"] == "completed"
    assert all(not decision["approval_required"] for decision in result["decisions"])


@pytest.mark.asyncio
async def test_low_confidence_plan_skips_specialists_and_requires_review() -> None:
    services = FakeServices(plan_confidence=0.2)
    graph = AgentGraphFactory(Settings(), services).compile(InMemorySaver())

    result = await graph.ainvoke(
        {"organization_id": str(uuid4()), "trace_id": "trace-2", "event": {"body": "unclear"}},
        {"configurable": {"thread_id": "workflow-2"}},
    )

    assert services.specialists == []
    assert result["status"] == "needs_review"


@pytest.mark.asyncio
async def test_retry_policy_retries_transient_planner_failure() -> None:
    services = FakeServices(fail_first_plan=True)
    graph = AgentGraphFactory(Settings(agent_node_retry_attempts=2), services).compile(InMemorySaver())

    await graph.ainvoke(
        {"organization_id": str(uuid4()), "trace_id": "trace-3", "event": {"body": "retry"}},
        {"configurable": {"thread_id": "workflow-3"}},
    )

    assert services.plan_calls == 2
