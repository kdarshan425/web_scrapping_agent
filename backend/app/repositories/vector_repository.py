"""Qdrant access for company-policy chunks. Only this file knows Qdrant exists."""
import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, FieldCondition, Filter, FilterSelector, MatchValue, PointStruct, VectorParams,
)

_NAMESPACE = uuid.UUID("6f1c2f0e-4b8a-4c53-9d7e-0a1b2c3d4e5f")


@dataclass
class PolicyHit:
    """One retrieved policy chunk."""
    filename: str
    text: str
    score: float


class PolicyVectorRepository:
    # def __init__(self, url: str, collection: str, dim: int) -> None:
    #     self.client = AsyncQdrantClient(url=url)
    #     self.collection = collection
    #     self.dim = dim

    def __init__(self, url: str, collection: str, dim: int, api_key: str = "") -> None:
        self.client = AsyncQdrantClient(url=url, api_key=api_key or None, check_compatibility=False)
        self.collection = collection
        self.dim = dim

    async def ensure_collection(self) -> None:
        if not await self.client.collection_exists(self.collection):
            await self.client.create_collection(
                self.collection, vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE)
            )

    async def upsert_chunks(
        self, document_id: str, filename: str, chunks: list[str], vectors: list[list[float]]
    ) -> None:
        points = [
            PointStruct(
                id=str(uuid.uuid5(_NAMESPACE, f"{document_id}:{i}")),  # deterministic -> idempotent
                vector=vec,
                payload={"document_id": document_id, "filename": filename, "chunk_index": i, "text": text},
            )
            for i, (text, vec) in enumerate(zip(chunks, vectors))
        ]
        await self.client.upsert(self.collection, points=points, wait=True)

    async def search(self, vector: list[float], top_k: int, min_score: float) -> list[PolicyHit]:
        res = await self.client.query_points(
            self.collection, query=vector, limit=top_k, score_threshold=min_score, with_payload=True
        )
        return [
            PolicyHit(filename=p.payload["filename"], text=p.payload["text"], score=float(p.score))
            for p in res.points
        ]

    async def delete_document(self, document_id: str) -> None:
        flt = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        await self.client.delete(self.collection, points_selector=FilterSelector(filter=flt), wait=True)
