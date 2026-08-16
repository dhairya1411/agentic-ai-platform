"""Declared action catalogue and executability checks for specialist proposals.

A proposal is only useful if it can actually be carried out. The confidence policy answers
"should a human approve this?" - it never asks "could this even run?". A live run surfaced
the gap: the GitHub specialist proposed a comment on `{"owner": "<owner>", "repo": "<repo>"}`
because the source event never named a repository. The policy passed it through, because a
placeholder is a perfectly confident, perfectly low-risk string.

Two layers close it:

1. **Declared actions only.** An action_type outside this catalogue is rejected. The platform
   is built on the premise that an agent cannot take an action nobody declared.
2. **Argument checks.** Shape, type, pattern - and a placeholder guard, because a schema
   cannot tell `<owner>` from a real account name, and free-text fields have no pattern
   to fail against.
"""

from __future__ import annotations

import re
from typing import Any

from agentic_ai_api.agents.contracts import ActionProposal
from agentic_ai_api.llm.contracts import ToolDefinition

# Values a model emits when it knows a field is required but the event never supplied it.
_PLACEHOLDER_PATTERNS = (
    re.compile(r"<[^>]{1,64}>"),  # <owner>, <repo>, <issue key>
    re.compile(r"\{\{[^}]{1,64}\}\}"),  # {{repo}}
    re.compile(r"^(tbd|todo|unknown|n/?a|none|null|xxx+|\.\.\.)$", re.IGNORECASE),
)

_SLACK_CHANNEL = r"^[#@]?[a-z0-9][a-z0-9._-]{0,79}$"
_JIRA_KEY = r"^[A-Z][A-Z0-9]{1,9}-[1-9][0-9]{0,6}$"
_GH_OWNER = r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$"
_GH_REPO = r"^[A-Za-z0-9._-]{1,100}$"


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> ToolDefinition:
    return ToolDefinition(
        name=name.replace(".", "_"),
        description=description,
        parameters={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


ACTION_CATALOGUE: dict[str, ToolDefinition] = {
    "slack.reply": _tool(
        "slack.reply",
        "Post a reply in the Slack channel the event came from.",
        {
            "channel": {"type": "string", "pattern": _SLACK_CHANNEL},
            "text": {"type": "string", "minLength": 1, "maxLength": 4000},
        },
        ["channel", "text"],
    ),
    "jira.transition": _tool(
        "jira.transition",
        "Move a Jira issue to a different workflow status.",
        {
            "issue_key": {"type": "string", "pattern": _JIRA_KEY},
            "status": {"type": "string", "minLength": 1, "maxLength": 100},
        },
        ["issue_key", "status"],
    ),
    "jira.comment": _tool(
        "jira.comment",
        "Add a comment to a Jira issue.",
        {
            "issue_key": {"type": "string", "pattern": _JIRA_KEY},
            "comment": {"type": "string", "minLength": 1, "maxLength": 8000},
        },
        ["issue_key", "comment"],
    ),
    "github.comment": _tool(
        "github.comment",
        "Comment on a GitHub pull request or issue.",
        {
            "owner": {"type": "string", "pattern": _GH_OWNER},
            "repo": {"type": "string", "pattern": _GH_REPO},
            "number": {"type": "integer", "minimum": 1},
            "body": {"type": "string", "minLength": 1, "maxLength": 8000},
        },
        ["owner", "repo", "number", "body"],
    ),
    "notification.send": _tool(
        "notification.send",
        "Notify a person or group outside the originating channel.",
        {
            "recipient": {"type": "string", "minLength": 1, "maxLength": 200},
            "message": {"type": "string", "minLength": 1, "maxLength": 2000},
        },
        ["recipient", "message"],
    ),
    "knowledge.store": _tool(
        "knowledge.store",
        "Persist a durable fact about the project to long-term memory.",
        {
            "title": {"type": "string", "minLength": 1, "maxLength": 200},
            "body": {"type": "string", "minLength": 1, "maxLength": 8000},
        },
        ["title", "body"],
    ),
}

DECLARED_ACTIONS: tuple[str, ...] = tuple(sorted(ACTION_CATALOGUE))


def _looks_like_placeholder(value: str) -> bool:
    return any(pattern.search(value.strip()) for pattern in _PLACEHOLDER_PATTERNS)


def _check_value(name: str, value: Any, schema: dict[str, Any]) -> str | None:
    """Validate one argument against its declared schema. Returns a reason, or None."""
    expected = schema.get("type")
    if expected == "integer":
        # bool is a subclass of int; a boolean where an id belongs is a mistake, not a value.
        if isinstance(value, bool) or not isinstance(value, int):
            return f"'{name}' must be an integer"
        minimum = schema.get("minimum")
        if isinstance(minimum, int) and value < minimum:
            return f"'{name}' must be at least {minimum}"
        return None

    if expected == "string":
        if not isinstance(value, str):
            return f"'{name}' must be a string"
        if _looks_like_placeholder(value):
            return f"'{name}' is an unresolved placeholder ({value.strip()[:40]!r})"
        minimum_length = schema.get("minLength")
        if isinstance(minimum_length, int) and len(value) < minimum_length:
            return f"'{name}' is shorter than {minimum_length} characters"
        maximum_length = schema.get("maxLength")
        if isinstance(maximum_length, int) and len(value) > maximum_length:
            return f"'{name}' exceeds {maximum_length} characters"
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.match(pattern, value):
            return f"'{name}' does not match the expected format for this field"
    return None


def rejection_reason(proposal: ActionProposal) -> str | None:
    """Return why a proposal cannot be executed, or None when it is well formed.

    Deliberately independent of confidence and risk. A proposal can be high-confidence,
    low-risk and still impossible to carry out.
    """
    definition = ACTION_CATALOGUE.get(proposal.action_type)
    if definition is None:
        return f"'{proposal.action_type}' is not a declared action"

    try:
        arguments = definition.validate_arguments(proposal.arguments)
    except ValueError as exc:
        return str(exc)

    properties: dict[str, Any] = definition.parameters["properties"]
    for name, value in arguments.items():
        reason = _check_value(name, value, properties[name])
        if reason is not None:
            return reason
    return None


def partition_proposals(
    proposals: list[ActionProposal],
) -> tuple[list[ActionProposal], list[dict[str, str]]]:
    """Split proposals into executable ones and rejections carrying their reason."""
    accepted: list[ActionProposal] = []
    rejected: list[dict[str, str]] = []
    for proposal in proposals:
        reason = rejection_reason(proposal)
        if reason is None:
            accepted.append(proposal)
        else:
            rejected.append({"action_type": proposal.action_type, "reason": reason})
    return accepted, rejected
