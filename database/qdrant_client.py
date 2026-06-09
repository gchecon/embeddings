import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from config import settings

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _client


def ensure_collection():
    client = get_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )


def upsert_points(points: list[dict]) -> None:
    client = get_client()
    structs = [
        PointStruct(
            id=p["id"],
            vector=p["vector"],
            payload=p["payload"],
        )
        for p in points
    ]
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=structs)


def delete_by_document_id(document_id: str) -> None:
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client = get_client()
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        ),
    )


def search(query_vector: list[float], limit: int = 10) -> list[dict]:
    client = get_client()
    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    return [
        {"score": r.score, "payload": r.payload}
        for r in results.points
    ]


def make_point_id() -> str:
    return str(uuid.uuid4())
