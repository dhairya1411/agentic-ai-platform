"""Stable error types and response models for the public API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """A validation or domain error detail safe to return to a client."""

    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    """The error payload nested in every API error response."""

    code: str
    message: str
    request_id: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Public API error envelope."""

    error: ErrorBody


class APIError(Exception):
    """An expected application error mapped to a safe HTTP response."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []
        self.headers = headers or {}


def validation_details(errors: list[dict[str, Any]]) -> list[ErrorDetail]:
    """Translate FastAPI validation diagnostics into the stable public contract."""
    return [
        ErrorDetail(field=".".join(str(part) for part in error["loc"]), message=error["msg"])
        for error in errors
    ]
