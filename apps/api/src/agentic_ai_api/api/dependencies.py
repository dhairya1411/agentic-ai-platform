"""FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_ai_api.core.config import Settings
from agentic_ai_api.infrastructure.database import Database


def get_app_settings(request: Request) -> Settings:
    """Get the immutable settings bound to this application instance."""
    return request.app.state.settings  # type: ignore[no-any-return]


def get_database(request: Request) -> Database:
    """Return the database lifecycle object for the current application."""
    return request.app.state.database  # type: ignore[no-any-return]


async def get_session(database: Database = Depends(get_database)) -> AsyncIterator[AsyncSession]:
    """Provide a transaction-scoped session to future repository dependencies."""
    async for session in database.session():
        yield session
