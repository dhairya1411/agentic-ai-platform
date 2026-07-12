"""Small deterministic prompt-regression harness for CI and review gates."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from agentic_ai_api.llm.contracts import ModelRequest, ModelResult


class EvaluationCase[OutputT: BaseModel](BaseModel):
    """A test fixture with an explicit assertion over structured output."""

    name: str
    request: ModelRequest[OutputT]


async def run_evaluation[OutputT: BaseModel](
    case: EvaluationCase[OutputT],
    complete: Callable[[ModelRequest[OutputT]], Awaitable[ModelResult[OutputT]]],
    assert_output: Callable[[OutputT], bool],
) -> bool:
    """Execute one deterministic assertion without persisting sensitive fixture content."""
    result = await complete(case.request)
    return assert_output(result.output)
