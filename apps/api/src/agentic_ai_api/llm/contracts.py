"""Strict, provider-independent contracts for model requests and tool calls."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ToolDefinition(BaseModel):
    """A JSON-schema function that a model may propose, never execute."""

    model_config = ConfigDict(frozen=True)
    name: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    description: str = Field(min_length=1, max_length=1_024)
    parameters: dict[str, Any]

    def as_openai_tool(self) -> dict[str, Any]:
        """Render the strict Responses API function-tool representation."""
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "strict": True,
        }

    def validate_arguments(self, arguments: str | Mapping[str, Any]) -> dict[str, Any]:
        """Validate a proposed call against the declared JSON schema."""
        value: Any = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
        validated = TypeAdapter(dict[str, Any]).validate_python(value)
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        if not isinstance(required, list) or not isinstance(properties, dict):
            raise ValueError("Tool parameters require JSON-schema properties and required fields")
        missing = set(required) - set(validated)
        unexpected = (
            set(validated) - set(properties)
            if self.parameters.get("additionalProperties") is False
            else set()
        )
        if missing or unexpected:
            message = f"Invalid tool arguments; missing={sorted(missing)}"
            raise ValueError(f"{message}, unexpected={sorted(unexpected)}")
        return validated


class PromptReference(BaseModel):
    """The exact persisted prompt version used for an invocation."""

    model_config = ConfigDict(frozen=True)
    id: UUID
    name: str
    version: int = Field(ge=1)
    template: str


class ModelRequest[OutputT: BaseModel](BaseModel):
    """A single bounded model request with an explicit structured output contract."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    organization_id: UUID
    trace_id: str = Field(min_length=1, max_length=64)
    prompt: PromptReference
    input: str = Field(min_length=1, max_length=100_000)
    output_model: type[OutputT]
    tools: tuple[ToolDefinition, ...] = ()


class ToolCall(BaseModel):
    """A validated model-proposed tool call awaiting later policy/execution phases."""

    model_config = ConfigDict(frozen=True)
    call_id: str
    name: str
    arguments: dict[str, Any]


class ModelResult[OutputT: BaseModel](BaseModel):
    """Validated model output plus non-sensitive operational metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)
    output: OutputT
    model: str
    provider_response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int = Field(ge=0)
    tool_calls: tuple[ToolCall, ...] = ()
