"""Tenant-scoped repository primitives.

Concrete repositories in later phases must derive from this boundary rather than
querying tenant-owned models with an unscoped AsyncSession.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from agentic_ai_api.domain.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class TenantRepository(Generic[ModelT]):
    """Provide organization-constrained select and persistence operations."""

    def __init__(self, session: AsyncSession, organization_id: UUID, model_type: type[ModelT]) -> None:
        self._session = session
        self._organization_id = organization_id
        self._model_type = model_type

    def query(self) -> Select[tuple[ModelT]]:
        """Start a query that is constrained to the repository tenant."""
        organization_column = getattr(self._model_type, "organization_id")
        return select(self._model_type).where(organization_column == self._organization_id)

    async def get(self, record_id: UUID) -> ModelT | None:
        """Load a record only if it belongs to this repository's tenant."""
        result = await self._session.scalars(self.query().where(self._model_type.id == record_id))
        return result.one_or_none()

    def add(self, entity: ModelT) -> None:
        """Stage an entity for persistence after verifying its organization scope."""
        if getattr(entity, "organization_id") != self._organization_id:
            raise ValueError("Entity organization_id does not match repository scope")
        self._session.add(entity)
