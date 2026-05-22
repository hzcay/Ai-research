from datetime import datetime, timezone
from uuid import uuid4

from src.application.ports.cache_port import SemanticCachePort

class QdrantSemanticCache(SemanticCachePort):
    def __init__(self, qdrant_client, collection_name="semantic_cache"):
        self.client = qdrant_client
        self.collection_name = collection_name

    async def get(self, query, query_vector, tenant_id, threshold=0.92):
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter={
                "must": [
                    {"key": "tenant_id", "match": {"value": tenant_id}}
                ]
            },
            limit=1,
            with_payload=True
        )

        if not results:
            return None

        best = results[0]

        if best.score < threshold:
            return None

        return {
            "answer": best.payload["answer"],
            "sources": best.payload.get("sources", []),
            "score": best.score,
            "cached_query": best.payload.get("query"),
            "cache_hit": True
        }

    async def set(self, query, query_vector, answer, sources, tenant_id, metadata=None):
        metadata = metadata or {}

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                {
                    "id": str(uuid4()),
                    "vector": query_vector,
                    "payload": {
                        "query": query,
                        "answer": answer,
                        "sources": sources,
                        "tenant_id": tenant_id,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        **metadata
                    }
                }
            ]
        )