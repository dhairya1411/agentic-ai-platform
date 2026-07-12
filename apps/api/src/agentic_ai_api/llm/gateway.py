"""Resilient OpenAI Responses API gateway with strict output validation."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol
from uuid import UUID

from openai import AsyncOpenAI
from pydantic import BaseModel

from agentic_ai_api.core.config import Settings
from agentic_ai_api.llm.contracts import ModelRequest, ModelResult, PromptReference, ToolCall
from agentic_ai_api.llm.redaction import Redactor


class ResponsesClient(Protocol):
    """Minimal SDK seam for deterministic gateway tests."""

    class _Responses(Protocol):
        async def create(self, **kwargs: Any) -> Any: ...

    responses: _Responses


class ModelGatewayError(RuntimeError):
    """Raised when every configured model attempt fails safely."""


class InvocationRecorder(Protocol):
    """Optional metadata-only persistence hook supplied by the application layer."""

    async def record_success[OutputT: BaseModel](
        self,
        *,
        organization_id: UUID,
        trace_id: str,
        prompt: PromptReference,
        result: ModelResult[OutputT],
    ) -> None: ...


class OpenAIModelGateway:
    """Submit redacted, schema-constrained requests with bounded fallback behavior."""

    def __init__(
        self,
        settings: Settings,
        client: ResponsesClient | None = None,
        recorder: InvocationRecorder | None = None,
    ) -> None:
        self._settings = settings
        api_key = settings.openai_api_key.get_secret_value()
        self._client: ResponsesClient = client or AsyncOpenAI(
            api_key=api_key or None, timeout=settings.llm_request_timeout_seconds
        )
        self._redactor = Redactor()
        self._recorder = recorder

    async def complete[OutputT: BaseModel](
        self, request: ModelRequest[OutputT]
    ) -> ModelResult[OutputT]:
        """Return a validated response; retry primary before one fallback attempt series."""
        input_text = request.input
        instructions = request.prompt.template
        if self._settings.llm_redact_pii:
            input_text = self._redactor.redact(input_text)
            instructions = self._redactor.redact(instructions)
        errors: list[Exception] = []
        models = tuple(
            dict.fromkeys((self._settings.llm_primary_model, self._settings.llm_fallback_model))
        )
        for model in models:
            for attempt in range(self._settings.llm_retry_attempts):
                started = time.perf_counter()
                try:
                    response = await self._client.responses.create(
                        model=model,
                        instructions=instructions,
                        input=input_text,
                        max_output_tokens=self._settings.llm_max_output_tokens,
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": request.output_model.__name__.lower(),
                                "schema": request.output_model.model_json_schema(),
                                "strict": True,
                            }
                        },
                        tools=[tool.as_openai_tool() for tool in request.tools],
                        metadata={
                            "trace_id": request.trace_id,
                            "prompt_version": str(request.prompt.version),
                        },
                    )
                    output = request.output_model.model_validate_json(response.output_text)
                    result = ModelResult(
                        output=output,
                        model=model,
                        provider_response_id=getattr(response, "id", None),
                        input_tokens=_usage(response, "input_tokens"),
                        output_tokens=_usage(response, "output_tokens"),
                        latency_ms=round((time.perf_counter() - started) * 1000),
                        tool_calls=tuple(_tool_calls(response, request)),
                    )
                    if self._recorder is not None:
                        await self._recorder.record_success(
                            organization_id=request.organization_id,
                            trace_id=request.trace_id,
                            prompt=request.prompt,
                            result=result,
                        )
                    return result
                except Exception as exc:  # SDK errors and schema violations are both fail-closed.
                    errors.append(exc)
                    if attempt + 1 < self._settings.llm_retry_attempts:
                        await asyncio.sleep(0.25 * (2**attempt))
        raise ModelGatewayError("All configured model attempts failed") from errors[-1]


def _usage(response: Any, field: str) -> int | None:
    usage = getattr(response, "usage", None)
    value = getattr(usage, field, None)
    return value if isinstance(value, int) else None


def _tool_calls[OutputT: BaseModel](
    response: Any, request: ModelRequest[OutputT]
) -> list[ToolCall]:
    definitions = {tool.name: tool for tool in request.tools}
    calls: list[ToolCall] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "function_call":
            continue
        name = getattr(item, "name", "")
        definition = definitions.get(name)
        if definition is None:
            raise ValueError(f"Model proposed undeclared tool: {name}")
        calls.append(
            ToolCall(
                call_id=str(getattr(item, "call_id", "")),
                name=name,
                arguments=definition.validate_arguments(getattr(item, "arguments", "{}")),
            )
        )
    return calls
