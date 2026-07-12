"""Gateway tests use a fake SDK response and never call a real model."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import BaseModel

from agentic_ai_api.core.config import Settings
from agentic_ai_api.llm.contracts import ModelRequest, PromptReference, ToolDefinition
from agentic_ai_api.llm.gateway import ModelGatewayError, OpenAIModelGateway
from agentic_ai_api.llm.redaction import Redactor


class WorkUpdate(BaseModel):
    status: str
    confidence: float


class FakeResponses:
    def __init__(self, responses: list[object]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeClient:
    def __init__(self, responses: list[object]) -> None:
        self.responses = FakeResponses(responses)


class FakeRecorder:
    def __init__(self) -> None:
        self.results: list[object] = []

    async def record_success(self, **kwargs: object) -> None:
        self.results.append(kwargs["result"])


def request(tools: tuple[ToolDefinition, ...] = ()) -> ModelRequest[WorkUpdate]:
    return ModelRequest(
        organization_id=uuid4(),
        trace_id="trace-123",
        prompt=PromptReference(
            id=uuid4(), name="work_update", version=2, template="Summarize safely."
        ),
        input="Contact jane@example.com; token sk-abcdefghijklmnopqrstuvwxyz",
        output_model=WorkUpdate,
        tools=tools,
    )


def response(output: str, output_items: list[object] | None = None) -> object:
    return SimpleNamespace(
        id="resp_123",
        output_text=output,
        output=output_items or [],
        usage=SimpleNamespace(input_tokens=11, output_tokens=5),
    )


@pytest.mark.asyncio
async def test_gateway_redacts_input_and_validates_structured_output() -> None:
    client = FakeClient([response('{"status":"done","confidence":0.9}')])
    gateway = OpenAIModelGateway(Settings(llm_retry_attempts=1), client=client)

    result = await gateway.complete(request())

    assert result.output == WorkUpdate(status="done", confidence=0.9)
    sent = client.responses.calls[0]["input"]
    assert sent == "Contact [REDACTED_EMAIL]; token [REDACTED_OPENAI_KEY]"
    assert client.responses.calls[0]["text"] is not None


@pytest.mark.asyncio
async def test_gateway_uses_fallback_after_primary_failure() -> None:
    client = FakeClient([RuntimeError("temporary"), response('{"status":"done","confidence":1.0}')])
    gateway = OpenAIModelGateway(
        Settings(llm_primary_model="primary", llm_fallback_model="fallback", llm_retry_attempts=1),
        client=client,
    )

    result = await gateway.complete(request())

    assert result.model == "fallback"
    assert [call["model"] for call in client.responses.calls] == ["primary", "fallback"]


@pytest.mark.asyncio
async def test_gateway_records_metadata_after_a_valid_response() -> None:
    recorder = FakeRecorder()
    client = FakeClient([response('{"status":"done","confidence":1.0}')])
    gateway = OpenAIModelGateway(
        Settings(llm_retry_attempts=1), client=client, recorder=recorder
    )

    await gateway.complete(request())

    assert len(recorder.results) == 1


@pytest.mark.asyncio
async def test_gateway_rejects_invalid_output_after_all_attempts() -> None:
    client = FakeClient([response('{"status": 3}')])
    gateway = OpenAIModelGateway(
        Settings(llm_fallback_model="gpt-5-mini", llm_retry_attempts=1), client=client
    )

    with pytest.raises(ModelGatewayError):
        await gateway.complete(request())


@pytest.mark.asyncio
async def test_gateway_validates_proposed_tool_arguments() -> None:
    tool = ToolDefinition(
        name="propose_jira_update",
        description="Propose an update only.",
        parameters={
            "type": "object",
            "properties": {"issue_key": {"type": "string"}},
            "required": ["issue_key"],
            "additionalProperties": False,
        },
    )
    call = SimpleNamespace(
        type="function_call", call_id="call_1", name=tool.name, arguments='{"issue_key":"ABC-1"}'
    )
    client = FakeClient([response('{"status":"done","confidence":1.0}', [call])])
    gateway = OpenAIModelGateway(Settings(llm_retry_attempts=1), client=client)

    result = await gateway.complete(request((tool,)))

    assert result.tool_calls[0].arguments == {"issue_key": "ABC-1"}


def test_redactor_removes_credentials_and_email() -> None:
    assert Redactor().redact("xoxb-123456789012 jane@example.com") == (
        "[REDACTED_SLACK_TOKEN] [REDACTED_EMAIL]"
    )
