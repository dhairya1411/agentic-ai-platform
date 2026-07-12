"""Persistence adapter for model-gateway operational telemetry."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_ai_api.domain.models import ModelInvocation
from agentic_ai_api.llm.contracts import ModelResult, PromptReference


class ModelInvocationRecorder:
    """Stage metadata-only invocation records in the caller's transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_success[OutputT: BaseModel](
        self,
        *,
        organization_id: UUID,
        trace_id: str,
        prompt: PromptReference,
        result: ModelResult[OutputT],
    ) -> None:
        """Store no prompt text, input, output, or proposed tool arguments."""
        self._session.add(
            ModelInvocation(
                organization_id=organization_id,
                prompt_template_id=prompt.id,
                trace_id=trace_id,
                provider_response_id=result.provider_response_id,
                model=result.model,
                status="completed",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=result.latency_ms,
                error_code=None,
            )
        )
