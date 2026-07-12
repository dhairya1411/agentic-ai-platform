"""Authorization-first hybrid ranking utilities independent of Qdrant transport."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from agentic_ai_api.memory.contracts import MemoryHit


@dataclass(frozen=True)
class MemoryRecord:
    id: UUID
    content: str
    source_type: str
    project_id: UUID | None
    access_tags: frozenset[str]


def access_allowed(record: MemoryRecord, access_tags: frozenset[str], project_id: UUID | None) -> bool:
    """Require project compatibility and full tag containment, not mere tag overlap."""
    return (record.project_id is None or record.project_id == project_id) and record.access_tags <= access_tags


def hybrid_rank(
    query: str,
    semantic_candidates: Iterable[tuple[MemoryRecord, float]],
    access_tags: frozenset[str],
    project_id: UUID | None,
    limit: int,
) -> list[MemoryHit]:
    """Fuse vector similarity with lexical overlap after authoritative authorization."""
    query_terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
    hits: list[MemoryHit] = []
    for record, semantic_score in semantic_candidates:
        if not access_allowed(record, access_tags, project_id):
            continue
        terms = set(re.findall(r"[a-z0-9_]+", record.content.lower()))
        lexical_score = len(query_terms & terms) / max(1, len(query_terms))
        score = 0.75 * semantic_score + 0.25 * lexical_score
        hits.append(MemoryHit(
            memory_id=record.id, content=record.content, source_type=record.source_type,
            project_id=record.project_id, score=score, semantic_score=semantic_score,
            lexical_score=lexical_score,
        ))
    return sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]
