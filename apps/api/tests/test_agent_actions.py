"""Proposal executability checks run independently of confidence and risk."""

from __future__ import annotations

import pytest

from agentic_ai_api.agents.actions import (
    ACTION_CATALOGUE,
    partition_proposals,
    rejection_reason,
)
from agentic_ai_api.agents.contracts import ActionProposal


def _proposal(action_type: str, arguments: dict[str, object]) -> ActionProposal:
    return ActionProposal(
        action_type=action_type,
        arguments=arguments,
        confidence=0.99,
        risk_level="low",
        rationale="High confidence and low risk on purpose; executability is a separate axis.",
    )


def test_well_formed_proposal_is_accepted() -> None:
    proposal = _proposal(
        "github.comment",
        {"owner": "dhairya1411", "repo": "agentic-ai-platform", "number": 482, "body": "Rolled back."},
    )
    assert rejection_reason(proposal) is None


def test_placeholder_arguments_are_rejected() -> None:
    """The failure found in the first live Groq run."""
    proposal = _proposal(
        "github.comment",
        {"owner": "<owner>", "repo": "<repo>", "number": 482, "body": "Rolled back."},
    )
    reason = rejection_reason(proposal)
    assert reason is not None
    assert "owner" in reason


def test_placeholder_in_free_text_is_rejected_without_a_pattern_to_fail() -> None:
    proposal = _proposal("jira.comment", {"issue_key": "ABC-1043", "comment": "{{summary}}"})
    reason = rejection_reason(proposal)
    assert reason is not None
    assert "placeholder" in reason


def test_undeclared_action_is_rejected() -> None:
    reason = rejection_reason(_proposal("jira.delete_project", {"key": "ABC"}))
    assert reason == "'jira.delete_project' is not a declared action"


def test_missing_required_argument_is_rejected() -> None:
    reason = rejection_reason(_proposal("jira.transition", {"issue_key": "ABC-1043"}))
    assert reason is not None
    assert "status" in reason


def test_unexpected_argument_is_rejected() -> None:
    reason = rejection_reason(
        _proposal("jira.transition", {"issue_key": "ABC-1043", "status": "In Progress", "force": True})
    )
    assert reason is not None
    assert "force" in reason


@pytest.mark.parametrize("issue_key", ["abc-1043", "ABC1043", "ABC-", "-1043", "<issue>"])
def test_malformed_issue_keys_are_rejected(issue_key: str) -> None:
    assert rejection_reason(_proposal("jira.comment", {"issue_key": issue_key, "comment": "x"})) is not None


def test_boolean_is_not_accepted_where_an_integer_is_declared() -> None:
    proposal = _proposal(
        "github.comment", {"owner": "dhairya1411", "repo": "repo", "number": True, "body": "x"}
    )
    reason = rejection_reason(proposal)
    assert reason is not None
    assert "integer" in reason


def test_partition_keeps_good_proposals_and_explains_the_rest() -> None:
    good = _proposal("jira.transition", {"issue_key": "ABC-1043", "status": "In Progress"})
    bad = _proposal("github.comment", {"owner": "<owner>", "repo": "<repo>", "number": 1, "body": "x"})
    accepted, rejected = partition_proposals([good, bad])

    assert accepted == [good]
    assert len(rejected) == 1
    assert rejected[0]["action_type"] == "github.comment"
    assert rejected[0]["reason"]


def test_every_catalogue_entry_declares_a_closed_schema() -> None:
    """A declared action with an open schema would let unchecked arguments through."""
    for action_type, definition in ACTION_CATALOGUE.items():
        assert definition.parameters["additionalProperties"] is False, action_type
        assert definition.parameters["required"], action_type
