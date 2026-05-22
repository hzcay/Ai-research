import json
from datetime import datetime, timezone
from uuid import uuid4

from src.application.ports.cache_port import SemanticCachePort

class QdrantSemanticCache(SemanticCachePort):
    def __init__(self, qdrant_client, redis_client, cache_ttl_seconds=86400, collection_name="semantic_cache"):
        self.client = qdrant_client
        self.redis = redis_client
        self.ttl = cache_ttl_seconds
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

        cache_id = best.payload.get("cache_id")
        if not cache_id:
            if "answer" in best.payload:
                return {
                    "answer": best.payload["answer"],
                    "sources": best.payload.get("sources", []),
                    "score": best.score,
                    "cached_query": best.payload.get("query"),
                    "cache_hit": True
                }
            return None

        cached_data = self.redis.get(cache_id)
        if not cached_data:
            return None

        payload = json.loads(cached_data)

        return {
            "answer": payload.get("answer"),
            "sources": payload.get("sources", []),
            "score": best.score,
            "cached_query": payload.get("query"),
            "cache_hit": True
        }

    async def set(self, query, query_vector, answer, sources, tenant_id, metadata=None):
        metadata = metadata or {}
        cache_id = str(uuid4())

        payload = {
            "query": query,
            "answer": answer,
            "sources": sources,
            "tenant_id": tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **metadata
        }
        
        self.redis.setex(cache_id, self.ttl, json.dumps(payload))

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                {
                    "id": cache_id,
                    "vector": query_vector,
                    "payload": {
                        "cache_id": cache_id,
                        "tenant_id": tenant_id
                    }
                }
            ]
        )