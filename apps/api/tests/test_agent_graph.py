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
                    # Must be a fully executable proposal: the graph now drops proposals
                    # whose arguments could not actually be carried out.
                    arguments={"issue_key": "ABC-1", "status": "Done"},
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


class PlaceholderServices(FakeServices):
    """Reproduces the first live Groq run: a confident proposal nobody could execute."""

    async def analyze(self, **kwargs: object) -> SpecialistOutput:
        self.specialists.append(str(kwargs["specialist"]))
        return SpecialistOutput(
            summary="Analysis complete",
            confidence=0.97,
            proposals=[
                ActionProposal(
                    action_type="github.comment",
                    arguments={"owner": "<owner>", "repo": "<repo>", "number": 482, "body": "Rolled back."},
                    confidence=0.96,
                    risk_level="low",
                    rationale="The event names PR 482 as the likely cause of the incident.",
                )
            ],
        )


@pytest.mark.asyncio
async def test_unexecutable_proposals_never_reach_the_policy() -> None:
    services = PlaceholderServices()
    graph = AgentGraphFactory(Settings(), services).compile(InMemorySaver())

    result = await graph.ainvoke(
        {"organization_id": str(uuid4()), "trace_id": "trace-4", "event": {"body": "500s after deploy"}},
        {"configurable": {"thread_id": "workflow-4"}},
    )

    assert result["proposals"] == []
    assert result["decisions"] == []
    rejected = result["rejected_proposals"]
    assert len(rejected) == 2  # one per specialist the planner routed to
    assert all(item["action_type"] == "github.comment" for item in rejected)
    assert all("placeholder" in item["reason"] for item in rejected)


class DisagreeingServices(FakeServices):
    """Two specialists reply to the same Slack channel with different text."""

    async def analyze(self, **kwargs: object) -> SpecialistOutput:
        specialist = str(kwargs["specialist"])
        self.specialists.append(specialist)
        return SpecialistOutput(
            summary="Analysis complete",
            confidence=0.97,
            proposals=[
                ActionProposal(
                    action_type="slack.reply",
                    arguments={"channel": "#eng-backend", "text": f"Reply written by {specialist}."},
                    confidence=0.95,
                    risk_level="low",
                    rationale="The event arrived in this channel and warrants acknowledgement.",
                )
            ],
        )


@pytest.mark.asyncio
async def test_duplicate_proposals_collapse_into_one_decision() -> None:
    services = FakeServices()
    graph = AgentGraphFactory(Settings(), services).compile(InMemorySaver())

    result = await graph.ainvoke(
        {"organization_id": str(uuid4()), "trace_id": "trace-5", "event": {"body": "done"}},
        {"configurable": {"thread_id": "workflow-5"}},
    )

    # Both specialists proposed the identical transition; one action, both credited.
    assert len(result["proposals"]) == 2
    assert len(result["decisions"]) == 1
    assert result["decisions"][0]["proposed_by"] == ["jira", "slack"]
    assert result["decisions"][0]["contested"] is False


@pytest.mark.asyncio
async def test_contested_proposals_cannot_auto_approve() -> None:
    services = DisagreeingServices()
    graph = AgentGraphFactory(Settings(), services).compile(InMemorySaver())

    result = await graph.ainvoke(
        {"organization_id": str(uuid4()), "trace_id": "trace-6", "event": {"body": "500s"}},
        {"configurable": {"thread_id": "workflow-6"}},
    )

    decisions = result["decisions"]
    assert len(decisions) == 2
    # Low risk and 0.95 confidence would otherwise clear the 0.92 threshold.
    assert all(decision["approval_required"] for decision in decisions)
    assert all(decision["contested"] for decision in decisions)
    assert all("same resource" in decision["reason"] for decision in decisions)
    assert result["status"] == "needs_review"
