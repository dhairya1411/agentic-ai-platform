"""FastAPI application factory and cross-cutting HTTP wiring."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from agentic_ai_api.api.routers.health import router as health_router
from agentic_ai_api.api.routers.dashboard import router as dashboard_router
from agentic_ai_api.api.routers.workspace import router as workspace_router
from agentic_ai_api.api.routers.auth import router as auth_router
from agentic_ai_api.core.config import Settings, get_settings
from agentic_ai_api.core.errors import (
    APIError,
    ErrorBody,
    ErrorDetail,
    ErrorResponse,
    validation_details,
)
from agentic_ai_api.core.logging import configure_logging, request_id_context
from agentic_ai_api.infrastructure.database import Database

logger = logging.getLogger("agentic_ai_api")
REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach or create a request identifier for correlation and client support."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid4()))
        token = request_id_context.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_context.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    """Build an error response that always includes the current request identifier."""
    payload = ErrorResponse(
        error=ErrorBody(
            code=code,
            message=message,
            request_id=request_id_context.get(),
            details=details or [],
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize process-level concerns and verify configured adapters."""
    settings: Settings = application.state.settings
    configure_logging(settings.log_level)
    database: Database = application.state.database
    await database.connect()
    logger.info("application_started environment=%s", settings.app_env)
    try:
        yield
    finally:
        await database.close()
        logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an independently testable FastAPI application instance."""
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        openapi_url=f"{resolved_settings.api_v1_prefix}/openapi.json",
        docs_url=f"{resolved_settings.api_v1_prefix}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database = Database(resolved_settings.database_url, enabled=resolved_settings.database_enabled)
    app.add_middleware(RequestIdMiddleware)
    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        )
    app.include_router(health_router, prefix=resolved_settings.api_v1_prefix)
    app.include_router(dashboard_router, prefix=resolved_settings.api_v1_prefix)
    app.include_router(workspace_router, prefix=resolved_settings.api_v1_prefix)
    app.include_router(auth_router, prefix=resolved_settings.api_v1_prefix)

    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError) -> JSONResponse:
        response = error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
        response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Request validation failed.",
            details=validation_details(exc.errors()),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_request_error")
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="An unexpected error occurred.",
        )

    return app


app = create_app()
