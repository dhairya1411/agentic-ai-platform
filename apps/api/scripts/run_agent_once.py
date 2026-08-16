"""Run one event through the agent graph against the configured LLM provider.

This is a wiring proof, not product surface. Nothing in the API constructs the graph yet,
and prompts live in the database with none seeded, so this script assembles the same
objects the application will eventually own - gateway, services, graph - and drives a
single event through them.

Usage (from apps/api, with the venv active):
    .\\.venv\\Scripts\\python.exe scripts\\run_agent_once.py
    .\\.venv\\Scripts\\python.exe scripts\\run_agent_once.py "Payments API is throwing 500s"

Reads configuration from .env, so it uses whatever provider LLM_BASE_URL points at.
"""

from __future__ import annotations

import asyncio
import json
import sys
from uuid import UUID, uuid4

from langgraph.checkpoint.memory import InMemorySaver

from agentic_ai_api.agents.graph import AgentGraphFactory
from agentic_ai_api.agents.services import GatewayAgentServices
from agentic_ai_api.core.config import get_settings
from agentic_ai_api.llm.contracts import PromptReference
from agentic_ai_api.llm.gateway import ModelGatewayError, OpenAIModelGateway

PLANNER_TEMPLATE = """You triage engineering work signals for a software project management platform.

Read the event and decide which specialists should analyse it.

Available specialists:
  slack        - conversation threads and team discussion
  github       - pull requests, commits, code review
  jira         - issues, tickets, sprint state
  meeting      - meeting notes and recordings
  standup      - daily standup updates
  reporting    - status reporting and metrics
  notification - alerting humans
  knowledge    - long-term project knowledge

Rules:
- Pick only specialists whose domain the event actually touches. Two or three is typical.
- confidence is your certainty in this routing, from 0 to 1. Be honest; low confidence
  routes the run to human review rather than to action.
- objective is one sentence describing what should be achieved.

Respond only with the required JSON object."""

SPECIALIST_TEMPLATE = """You are the {specialist} specialist in a governed agent platform.

You analyse the event and propose actions. You never execute anything - every proposal is
reviewed by a confidence and risk policy before a human sees it.

For each proposal:
- action_type is lowercase dotted, e.g. jira.transition, slack.reply, github.comment
- risk_level is low, medium or high. Anything that writes to a system another human relies
  on, or that is hard to reverse, is not low.
- confidence is your certainty this action is correct, from 0 to 1.
- rationale must cite what in the event justifies the action.

Propose nothing if the event does not warrant action in your domain. An empty proposal list
is a valid, often correct answer.

Respond only with the required JSON object."""

DEFAULT_EVENT = {
    "source": "slack",
    "channel": "#eng-backend",
    "author": "priya",
    "body": (
        "Heads up - the checkout service has been returning 500s since the 14:20 deploy. "
        "I've rolled back. PR #482 looks like the cause. ABC-1043 should probably move back "
        "to In Progress."
    ),
}


def _prompt(name: str, template: str) -> PromptReference:
    """Build an in-memory prompt reference; the real system loads these from the database."""
    return PromptReference(id=uuid4(), name=name, version=1, template=template)


async def main() -> int:
    settings = get_settings()
    event = dict(DEFAULT_EVENT)
    if len(sys.argv) > 1:
        event = {"source": "manual", "body": " ".join(sys.argv[1:])}

    print(f"provider   : {settings.llm_base_url or 'https://api.openai.com/v1 (default)'}")
    print(f"primary    : {settings.llm_primary_model}")
    print(f"fallback   : {settings.llm_fallback_model}")
    if not settings.openai_api_key.get_secret_value():
        print("\nOPENAI_API_KEY is empty. Put your Groq key in .env and re-run.")
        return 2
    print(f"\nevent      : {event['body'][:100]}...\n")

    gateway = OpenAIModelGateway(settings)
    services = GatewayAgentServices(
        gateway=gateway,
        planner_prompt=_prompt("planner", PLANNER_TEMPLATE),
        specialist_prompts={
            name: _prompt(f"specialist.{name}", SPECIALIST_TEMPLATE.format(specialist=name))
            for name in (
                "slack", "github", "jira", "meeting",
                "standup", "reporting", "notification", "knowledge",
            )
        },
    )
    graph = AgentGraphFactory(settings, services).compile(InMemorySaver())

    organization_id = UUID("00000000-0000-0000-0000-000000000001")
    try:
        result = await graph.ainvoke(
            {
                "organization_id": str(organization_id),
                "trace_id": f"local-{uuid4().hex[:8]}",
                "event": event,
            },
            {"configurable": {"thread_id": f"run-{uuid4().hex[:8]}"}},
        )
    except ModelGatewayError as exc:
        print(f"gateway failed after all retries: {exc}")
        print(f"underlying cause: {exc.__cause__!r}")
        return 1

    plan = result.get("plan", {})
    print("PLAN")
    print(f"  objective   : {plan.get('objective')}")
    print(f"  specialists : {plan.get('specialists')}")
    print(f"  confidence  : {plan.get('confidence')}")

    print(f"\nPROPOSALS ({len(result.get('proposals', []))})")
    for proposal in result.get("proposals", []):
        print(f"  {proposal['action_type']}  risk={proposal['risk_level']}  conf={proposal['confidence']}")
        print(f"      args   : {json.dumps(proposal.get('arguments', {}))}")
        print(f"      because: {proposal['rationale'][:140]}")

    print(f"\nDECISIONS ({len(result.get('decisions', []))})")
    for decision in result.get("decisions", []):
        gate = "NEEDS APPROVAL" if decision["approval_required"] else "auto-approvable"
        print(f"  {decision['action_type']:<24} {gate}")
        print(f"      {decision['reason']}")

    print(f"\nfinal status: {result.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
