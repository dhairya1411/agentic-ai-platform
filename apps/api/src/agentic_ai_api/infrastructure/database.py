"""Async SQLAlchemy database lifecycle and tenant-scoped session helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class Database:
    """Own the async engine and expose sessions with transaction boundaries."""

    def __init__(self, url: str, *, enabled: bool) -> None:
        self._enabled = enabled
        self._engine: AsyncEngine | None = (
            create_async_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20) if enabled else None
        )
        self._session_factory = (
            async_sessionmaker(self._engine, expire_on_commit=False) if self._engine is not None else None
        )

    @property
    def enabled(self) -> bool:
        """Whether this process is configured to use a database."""
        return self._enabled

    async def connect(self) -> None:
        """Fail startup early when the configured database is unreachable."""
        if self._engine is None:
            return
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def close(self) -> None:
        """Release all database connections during process shutdown."""
        if self._engine is not None:
            await self._engine.dispose()

    async def healthcheck(self) -> bool:
        """Return database reachability without leaking driver errors."""
        if self._engine is None:
            return True
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a transaction-scoped session and roll back on unhandled errors."""
        if self._session_factory is None:
            raise RuntimeError("Database access is disabled for this application instance")
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def tenant_session(self, organization_id: UUID) -> AsyncIterator[AsyncSession]:
        """Yield a session whose PostgreSQL RLS context is locked to one tenant."""
        async for session in self.session():
            await session.execute(
                text("SELECT set_config('app.current_organization_id', :organization_id, true)"),
                {"organization_id": str(organization_id)},
            )
            yield session
