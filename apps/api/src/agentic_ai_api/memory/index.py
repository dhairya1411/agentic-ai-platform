"""Embedding and Qdrant adapters; the index contains no authoritative memory content."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient, models

from agentic_ai_api.core.config import Settings


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class MemoryVectorIndex(Protocol):
    async def ensure_collection(self) -> None: ...
    async def upsert(self, memory_id: UUID, vector: list[float], payload: dict[str, Any]) -> None: ...
    async def search(self, vector: list[float], organization_id: UUID, limit: int) -> list[tuple[UUID, float]]: ...
    async def delete(self, memory_ids: list[UUID]) -> None: ...


class OpenAIEmbeddingProvider:
    """Generate embeddings with the configured OpenAI embedding model."""

    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value() or None)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model, input=text, dimensions=self._dimensions
        )
        return list(response.data[0].embedding)


class QdrantMemoryIndex:
    """Derived vector index with mandatory organization filtering on every query."""

    def __init__(self, settings: Settings, client: AsyncQdrantClient | None = None) -> None:
        self._collection = settings.memory_collection_name
        self._dimensions = settings.embedding_dimensions
        self._client = client or AsyncQdrantClient(url=settings.qdrant_url)

    async def ensure_collection(self) -> None:
        if not await self._client.collection_exists(self._collection):
            await self._client.create_collection(
                self._collection,
                vectors_config=models.VectorParams(size=self._dimensions, distance=models.Distance.COSINE),
            )
            await self._client.create_payload_index(
                self._collection, "organization_id", models.PayloadSchemaType.KEYWORD
            )
            await self._client.create_payload_index(
                self._collection, "project_id", models.PayloadSchemaType.KEYWORD
            )

    async def upsert(self, memory_id: UUID, vector: list[float], payload: dict[str, Any]) -> None:
        await self._client.upsert(
            self._collection, [models.PointStruct(id=str(memory_id), vector=vector, payload=payload)], wait=True
        )

    async def search(self, vector: list[float], organization_id: UUID, limit: int) -> list[tuple[UUID, float]]:
        response = await self._client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="organization_id", match=models.MatchValue(value=str(organization_id)))]
            ),
            limit=limit,
            with_payload=False,
        )
        return [(UUID(str(point.id)), float(point.score)) for point in response.points]

    async def delete(self, memory_ids: list[UUID]) -> None:
        if memory_ids:
            await self._client.delete(
                self._collection,
                points_selector=models.PointIdsList(points=[str(memory_id) for memory_id in memory_ids]),
                wait=True,
            )
