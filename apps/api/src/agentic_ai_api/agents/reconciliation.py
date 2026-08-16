"""Fan-in for specialist proposals: collapse duplicates, surface disagreement.

The supervisor fans an event out to several specialists, each of which analyses it in
isolation. Nothing fanned back in, so a live run produced five proposals for two real
actions: three identical Jira transitions, and two Slack replies to the same channel with
different text. Both Slack replies scored above the auto-approval threshold at low risk, so
an execution layer would have posted two messages to #eng-backend.

Two distinct situations, deliberately handled differently:

* **Identical proposals** are agreement. Collapse them into one and record who proposed it.
  Three specialists reaching the same conclusion is corroboration, not three units of work.
* **Different payloads aimed at the same target** are disagreement. Keep them all, mark them
  contested, and deny auto-approval. Two specialists proposing different replies to the same
  channel is a decision a human should make, not an ordering the system picks by luck.
"""

from __future__ import annotations

import json
from typing import Any

# The arguments that identify what a proposal acts on. Two proposals sharing an action_type
# and these values are aimed at the same thing, whatever else differs.
TARGET_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "slack.reply": ("channel",),
    "jira.transition": ("issue_key",),
    "jira.comment": ("issue_key",),
    "github.comment": ("owner", "repo", "number"),
    "notification.send": ("recipient",),
    "knowledge.store": ("title",),
}

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def _identity(proposal: dict[str, Any]) -> str:
    """Everything that makes two proposals the same action with the same payload."""
    arguments = json.dumps(proposal.get("arguments", {}), sort_keys=True)
    return f"{proposal['action_type']}::{arguments}"


def _target(proposal: dict[str, Any]) -> str:
    """What the proposal acts on, ignoring payload differences."""
    action_type = str(proposal["action_type"])
    keys = TARGET_ARGUMENTS.get(action_type)
    arguments = proposal.get("arguments", {})
    if keys is None:
        # Undeclared targets fall back to identity, so nothing is wrongly grouped together.
        return _identity(proposal)
    values = {key: arguments.get(key) for key in keys}
    return f"{action_type}::{json.dumps(values, sort_keys=True)}"


def _merge(duplicates: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine identical proposals conservatively: highest risk, lowest confidence."""
    first = duplicates[0]
    risk = max((str(item["risk_level"]) for item in duplicates), key=lambda level: _RISK_ORDER[level])
    confidence = min(float(item["confidence"]) for item in duplicates)
    proposed_by = sorted({str(item["specialist"]) for item in duplicates if item.get("specialist")})
    return {
        "action_type": first["action_type"],
        "arguments": first.get("arguments", {}),
        "risk_level": risk,
        "confidence": confidence,
        "rationale": first["rationale"],
        "proposed_by": proposed_by,
        "contested": False,
    }


def reconcile(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse identical proposals and mark those competing for the same target.

    Order is preserved by first appearance so runs stay deterministic.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for proposal in proposals:
        key = _identity(proposal)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(proposal)

    merged = [_merge(grouped[key]) for key in order]

    # A target reached by more than one distinct payload is contested.
    targets: dict[str, int] = {}
    for item in merged:
        target = _target(item)
        targets[target] = targets.get(target, 0) + 1
    for item in merged:
        if targets[_target(item)] > 1:
            item["contested"] = True
    return merged
