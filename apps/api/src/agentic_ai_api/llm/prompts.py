"""Tenant-scoped prompt template persistence and deterministic rendering."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_ai_api.domain.models import PromptTemplate
from agentic_ai_api.llm.contracts import PromptReference


class PromptRepository:
    """Resolve only enabled prompt versions inside one organization boundary."""

    def __init__(self, session: AsyncSession, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    async def get_active(self, name: str) -> PromptReference | None:
        statement = (
            select(PromptTemplate)
            .where(
                PromptTemplate.organization_id == self._organization_id,
                PromptTemplate.name == name,
                PromptTemplate.enabled.is_(True),
            )
            .order_by(desc(PromptTemplate.version))
            .limit(1)
        )
        row = (await self._session.scalars(statement)).first()
        if row is None:
            return None
        return PromptReference(id=row.id, name=row.name, version=row.version, template=row.template)


def render_prompt(template: str, variables: dict[str, Any]) -> str:
    """Render named variables only; fail closed for missing or unused inputs."""
    try:
        return template.format_map(_StrictMapping(variables))
    except (KeyError, ValueError) as exc:
        raise ValueError("Prompt variables do not match the stored template") from exc


class _StrictMapping(dict[str, Any]):
    def __missing__(self, key: str) -> Any:
        raise KeyError(key)
