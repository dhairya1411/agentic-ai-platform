"""Gateway-backed planner and specialist adapters used by LangGraph nodes."""

from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID

from agentic_ai_api.agents.contracts import PlanOutput, SpecialistName, SpecialistOutput
from agentic_ai_api.llm.contracts import ModelRequest, PromptReference
from agentic_ai_api.llm.gateway import OpenAIModelGateway


class AgentServices(Protocol):
    """Side-effect-free analysis boundary that makes graph nodes easy to test."""

    async def plan(self, *, organization_id: UUID, trace_id: str, event: dict[str, object]) -> PlanOutput: ...

    async def analyze(
        self,
        *,
        specialist: SpecialistName,
        organization_id: UUID,
        trace_id: str,
        event: dict[str, object],
        plan: PlanOutput,
    ) -> SpecialistOutput: ...


class GatewayAgentServices:
    """Route planner and specialist requests through the Phase 6 model gateway."""

    def __init__(
        self,
        gateway: OpenAIModelGateway,
        planner_prompt: PromptReference,
        specialist_prompts: dict[SpecialistName, PromptReference],
    ) -> None:
        self._gateway = gateway
        self._planner_prompt = planner_prompt
        self._specialist_prompts = specialist_prompts

    async def plan(self, *, organization_id: UUID, trace_id: str, event: dict[str, object]) -> PlanOutput:
        result = await self._gateway.complete(
            ModelRequest(
                organization_id=organization_id,
                trace_id=trace_id,
                prompt=self._planner_prompt,
                input=json.dumps(event, sort_keys=True),
                output_model=PlanOutput,
            )
        )
        return result.output

    async def analyze(
        self,
        *,
        specialist: SpecialistName,
        organization_id: UUID,
        trace_id: str,
        event: dict[str, object],
        plan: PlanOutput,
    ) -> SpecialistOutput:
        prompt = self._specialist_prompts.get(specialist)
        if prompt is None:
            raise ValueError(f"No prompt is configured for specialist '{specialist}'")
        result = await self._gateway.complete(
            ModelRequest(
                organization_id=organization_id,
                trace_id=trace_id,
                prompt=prompt,
                input=json.dumps(
                    {"event": event, "plan": plan.model_dump(mode="json")}, sort_keys=True
                ),
                output_model=SpecialistOutput,
            )
        )
        return result.output
