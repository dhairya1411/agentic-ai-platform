"""LangGraph topology for planning, supervision, specialist analysis, and policy."""

from __future__ import annotations

from typing import Any, Literal, TypedDict, cast
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from agentic_ai_api.agents.actions import partition_proposals
from agentic_ai_api.agents.contracts import ActionProposal, ConfidenceDecision, PlanOutput, SpecialistName
from agentic_ai_api.agents.reconciliation import reconcile
from agentic_ai_api.agents.services import AgentServices
from agentic_ai_api.core.config import Settings
from agentic_ai_api.llm.gateway import ModelGatewayError


def is_transient_node_failure(exc: Exception) -> bool:
    """Decide whether a failed node is worth another attempt.

    LangGraph's default ``retry_on`` refuses to retry ``RuntimeError``, treating it as a
    programming fault. ``ModelGatewayError`` subclasses ``RuntimeError``, so relying on that
    default silently disables retries for the exact failure this policy exists to absorb.
    Deterministic faults - bad schema, bad arguments, bad code - never improve on retry.
    """
    return isinstance(exc, ModelGatewayError | ConnectionError | TimeoutError)


NodeName = Literal[
    "planner", "supervisor", "slack", "github", "jira", "meeting", "standup", "reporting",
    "notification", "knowledge", "confidence_policy",
]


class AgentState(TypedDict, total=False):
    """JSON-serializable checkpoint state for one tenant-scoped workflow run."""

    organization_id: str
    trace_id: str
    event: dict[str, object]
    plan: dict[str, object]
    pending_specialists: list[SpecialistName]
    completed_specialists: list[SpecialistName]
    proposals: list[dict[str, object]]
    # Proposals dropped before policy because they could not be executed as written.
    rejected_proposals: list[dict[str, str]]
    decisions: list[dict[str, object]]
    status: Literal["running", "completed", "needs_review", "rejected"]


class AgentGraphFactory:
    """Build a deterministic graph; external effects are forbidden in every node."""

    def __init__(self, settings: Settings, services: AgentServices) -> None:
        self._settings = settings
        self._services = services

    def compile(self, checkpointer: Any) -> Any:
        """Compile with an injected checkpointer so production owns persistence lifecycle."""
        graph = StateGraph(AgentState)
        retry = RetryPolicy(
            max_attempts=self._settings.agent_node_retry_attempts,
            retry_on=is_transient_node_failure,
        )
        graph.add_node("planner", self._planner, retry_policy=retry)
        graph.add_node("supervisor", self._supervisor)
        for specialist in _SPECIALISTS:
            graph.add_node(specialist, self._specialist_node(specialist), retry_policy=retry)
        graph.add_node("confidence_policy", self._confidence_policy)
        graph.add_edge(START, "planner")
        graph.add_edge("planner", "supervisor")
        graph.add_conditional_edges("supervisor", self._next_specialist)
        for specialist in _SPECIALISTS:
            graph.add_conditional_edges(specialist, self._next_specialist)
        graph.add_edge("confidence_policy", END)
        return graph.compile(checkpointer=checkpointer)

    async def _planner(self, state: AgentState) -> AgentState:
        plan = await self._services.plan(
            organization_id=UUID(state["organization_id"]),
            trace_id=state["trace_id"],
            event=state["event"],
        )
        return {"plan": plan.model_dump(mode="json"), "status": "running"}

    def _supervisor(self, state: AgentState) -> AgentState:
        plan = PlanOutput.model_validate(state["plan"])
        unique_specialists = list(dict.fromkeys(plan.specialists))
        if plan.confidence < self._settings.agent_min_confidence:
            return {"pending_specialists": [], "status": "needs_review"}
        return {
            "pending_specialists": unique_specialists,
            "completed_specialists": [],
            "proposals": [],
            "status": "running",
        }

    def _specialist_node(self, specialist: SpecialistName) -> Any:
        async def run(state: AgentState) -> AgentState:
            plan = PlanOutput.model_validate(state["plan"])
            result = await self._services.analyze(
                specialist=specialist,
                organization_id=UUID(state["organization_id"]),
                trace_id=state["trace_id"],
                event=state["event"],
                plan=plan,
            )
            pending = [item for item in state.get("pending_specialists", []) if item != specialist]
            completed = [*state.get("completed_specialists", []), specialist]
            # Drop proposals that cannot be executed before they reach the policy. The policy
            # weighs confidence and risk; it has no view on whether the arguments are usable.
            accepted, rejected = partition_proposals(list(result.proposals))
            proposals = [
                *state.get("proposals", []),
                # Attribution travels with the proposal so reconciliation and the audit log
                # can both answer "which specialist wanted this?".
                *({**item.model_dump(mode="json"), "specialist": specialist} for item in accepted),
            ]
            rejections = [
                *state.get("rejected_proposals", []),
                *({**item, "specialist": specialist} for item in rejected),
            ]
            return {
                "pending_specialists": pending,
                "completed_specialists": completed,
                "proposals": proposals,
                "rejected_proposals": rejections,
            }

        return run

    def _next_specialist(self, state: AgentState) -> NodeName:
        pending = state.get("pending_specialists", [])
        if pending:
            return cast(NodeName, pending[0])
        return "confidence_policy"

    def _confidence_policy(self, state: AgentState) -> AgentState:
        decisions: list[dict[str, object]] = []
        requires_review = state.get("status") == "needs_review"
        # Fan-in: specialists worked independently, so the same action can arrive several
        # times, and two specialists can target one resource with different payloads.
        reconciled = reconcile(list(state.get("proposals", [])))
        for item in reconciled:
            proposal = ActionProposal.model_validate(item)
            contested = bool(item["contested"])
            proposed_by = [str(name) for name in item["proposed_by"]]
            reasons: list[str] = []
            if requires_review:
                reasons.append("the plan itself was routed for review")
            if contested:
                reasons.append("another proposal targets the same resource with different arguments")
            if proposal.risk_level != "low":
                reasons.append(f"risk level is {proposal.risk_level}")
            if proposal.confidence < self._settings.agent_auto_approval_confidence:
                reasons.append(
                    f"confidence {proposal.confidence:.2f} is below the "
                    f"{self._settings.agent_auto_approval_confidence:.2f} auto-approval threshold"
                )

            approval_required = bool(reasons)
            reason = (
                f"Requires human approval: {'; '.join(reasons)}."
                if approval_required
                else "Eligible for later policy evaluation."
            )
            decision = ConfidenceDecision(
                action_type=proposal.action_type,
                approval_required=approval_required,
                reason=reason,
                proposed_by=proposed_by,
                contested=contested,
            )
            decisions.append(decision.model_dump(mode="json"))
        return {
            "decisions": decisions,
            "status": "needs_review"
            if requires_review or any(d["approval_required"] for d in decisions)
            else "completed",
        }


_SPECIALISTS: tuple[SpecialistName, ...] = (
    "slack", "github", "jira", "meeting", "standup", "reporting", "notification", "knowledge"
)
