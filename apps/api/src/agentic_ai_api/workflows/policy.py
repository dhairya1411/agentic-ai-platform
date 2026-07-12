"""Deterministic proposal policy."""

from dataclasses import dataclass

from agentic_ai_api.agents.contracts import ActionProposal


@dataclass(frozen=True)
class PolicyDecision:
    status: str
    reason: str


def evaluate(proposal: ActionProposal, threshold: float) -> PolicyDecision:
    if proposal.risk_level == "low" and proposal.confidence >= threshold:
        return PolicyDecision("permitted", "Low-risk proposal meets threshold.")
    return PolicyDecision("pending_approval", "Human approval required by risk/confidence policy.")
