"""Review, index, retrieve, and expire governed memory records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_ai_api.core.config import Settings
from agentic_ai_api.domain.models import Memory, MemoryRetrievalLog
from agentic_ai_api.memory.contracts import MemoryCandidate, MemoryHit
from agentic_ai_api.memory.index import EmbeddingProvider, MemoryVectorIndex
from agentic_ai_api.memory.retrieval import MemoryRecord, hybrid_rank


class MemoryService:
    """Keep PostgreSQL authoritative while maintaining a rebuildable vector index."""

    def __init__(
        self, session: AsyncSession, settings: Settings, embeddings: EmbeddingProvider, index: MemoryVectorIndex
    ) -> None:
        self._session, self._settings, self._embeddings, self._index = session, settings, embeddings, index

    async def stage(self, organization_id: UUID, candidate: MemoryCandidate) -> Memory:
        """Persist a candidate for review; it is not searchable until approved."""
        expires_at = candidate.expires_at or datetime.now(UTC) + timedelta(
            days=self._settings.memory_default_retention_days
        )
        memory = Memory(
            organization_id=organization_id, project_id=candidate.project_id, source_type=candidate.source_type,
            source_ref=candidate.source_ref, content=candidate.content, importance=candidate.importance,
            access_tags=sorted(candidate.access_tags), status="pending_review", expires_at=expires_at,
        )
        self._session.add(memory)
        await self._session.flush()
        return memory

    async def approve(self, memory: Memory) -> None:
        """Activate and index a reviewed memory using non-sensitive retrieval payload only."""
        if memory.status != "pending_review":
            raise ValueError("Only pending memory candidates can be approved")
        await self._index.ensure_collection()
        vector = await self._embeddings.embed(memory.content)
        await self._index.upsert(
            memory.id, vector,
            {"organization_id": str(memory.organization_id),
             "project_id": str(memory.project_id) if memory.project_id else None,
             "source_type": memory.source_type},
        )
        memory.qdrant_point_id, memory.status = memory.id, "active"

    async def retrieve(
        self, *, organization_id: UUID, query: str, access_tags: frozenset[str], project_id: UUID | None,
        workflow_run_id: UUID | None = None, limit: int = 8,
    ) -> list[MemoryHit]:
        """Vector-search candidates, then re-authorize against authoritative PostgreSQL rows."""
        vector = await self._embeddings.embed(query)
        candidates = await self._index.search(vector, organization_id, self._settings.memory_retrieval_candidate_limit)
        ids = [memory_id for memory_id, _ in candidates]
        if not ids:
            return []
        now = datetime.now(UTC)
        rows = await self._session.scalars(select(Memory).where(
            Memory.organization_id == organization_id, Memory.id.in_(ids), Memory.status == "active",
            (Memory.expires_at.is_(None)) | (Memory.expires_at > now),
        ))
        records = {row.id: row for row in rows}
        ranked = hybrid_rank(query, (
            (MemoryRecord(row.id, row.content, row.source_type, row.project_id, frozenset(row.access_tags)), score)
            for memory_id, score in candidates if (row := records.get(memory_id)) is not None
        ), access_tags, project_id, limit)
        for rank, hit in enumerate(ranked, start=1):
            self._session.add(MemoryRetrievalLog(
                organization_id=organization_id, workflow_run_id=workflow_run_id, memory_id=hit.memory_id,
                rank=rank, score=hit.score, used=False,
            ))
        return ranked

    async def expire_due(self, organization_id: UUID) -> int:
        """Remove expired points and mark records before they can be retrieved again."""
        rows = list(await self._session.scalars(select(Memory).where(
            Memory.organization_id == organization_id,
            Memory.status == "active",
            Memory.expires_at <= datetime.now(UTC),
        )))
        await self._index.delete([row.id for row in rows])
        for row in rows:
            row.status = "expired"
        return len(rows)
