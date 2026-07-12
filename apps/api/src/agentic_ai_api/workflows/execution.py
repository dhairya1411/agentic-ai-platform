"""Idempotent execution boundary with mandatory verification."""

from collections.abc import Awaitable, Callable
from typing import Any


class WorkflowExecutionError(RuntimeError):
    pass


async def execute_and_verify(
    execute: Callable[[], Awaitable[dict[str, Any]]], verify: Callable[[dict[str, Any]], Awaitable[bool]]
) -> dict[str, Any]:
    result = await execute()
    if not await verify(result):
        raise WorkflowExecutionError("External action could not be verified")
    return result
