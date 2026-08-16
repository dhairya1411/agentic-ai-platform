"""Fan-in behaviour: agreement collapses, disagreement is surfaced."""

from __future__ import annotations

from agentic_ai_api.agents.reconciliation import reconcile


def _proposal(
    action_type: str,
    arguments: dict[str, object],
    specialist: str,
    *,
    confidence: float = 0.95,
    risk_level: str = "low",
) -> dict[str, object]:
    return {
        "action_type": action_type,
        "arguments": arguments,
        "confidence": confidence,
        "risk_level": risk_level,
        "rationale": "Recorded so the audit log can explain the action.",
        "specialist": specialist,
    }


def test_identical_proposals_collapse_and_record_every_proposer() -> None:
    """Three specialists reaching the same conclusion is one action, corroborated."""
    transition = {"issue_key": "ABC-1043", "status": "In Progress"}
    reconciled = reconcile(
        [
            _proposal("jira.transition", transition, "slack"),
            _proposal("jira.transition", transition, "jira"),
            _proposal("jira.transition", transition, "github"),
        ]
    )

    assert len(reconciled) == 1
    assert reconciled[0]["proposed_by"] == ["github", "jira", "slack"]
    assert reconciled[0]["contested"] is False


def test_same_target_with_different_payloads_is_contested() -> None:
    """The two Slack replies from the live run: same channel, different text."""
    reconciled = reconcile(
        [
            _proposal("slack.reply", {"channel": "#eng-backend", "text": "Thanks, reviewing."}, "slack"),
            _proposal("slack.reply", {"channel": "#eng-backend", "text": "Rolled back, see PR."}, "github"),
        ]
    )

    assert len(reconciled) == 2
    assert all(item["contested"] is True for item in reconciled)


def test_same_action_on_different_targets_is_not_contested() -> None:
    reconciled = reconcile(
        [
            _proposal("jira.comment", {"issue_key": "ABC-1043", "comment": "a"}, "jira"),
            _proposal("jira.comment", {"issue_key": "ABC-2000", "comment": "b"}, "slack"),
        ]
    )

    assert len(reconciled) == 2
    assert all(item["contested"] is False for item in reconciled)


def test_merge_is_conservative_on_risk_and_confidence() -> None:
    """A duplicate must never be safer than the least safe way it was proposed."""
    arguments = {"issue_key": "ABC-1043", "status": "Done"}
    reconciled = reconcile(
        [
            _proposal("jira.transition", arguments, "jira", confidence=0.99, risk_level="low"),
            _proposal("jira.transition", arguments, "slack", confidence=0.71, risk_level="high"),
        ]
    )

    assert len(reconciled) == 1
    assert reconciled[0]["risk_level"] == "high"
    assert reconciled[0]["confidence"] == 0.71


def test_order_is_preserved_by_first_appearance() -> None:
    reconciled = reconcile(
        [
            _proposal("slack.reply", {"channel": "#a", "text": "x"}, "slack"),
            _proposal("jira.comment", {"issue_key": "ABC-1", "comment": "y"}, "jira"),
            _proposal("slack.reply", {"channel": "#a", "text": "x"}, "github"),
        ]
    )

    assert [item["action_type"] for item in reconciled] == ["slack.reply", "jira.comment"]


def test_empty_input_produces_no_decisions() -> None:
    assert reconcile([]) == []
