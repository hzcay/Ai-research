import json
from datetime import datetime, timezone
from uuid import uuid4
from qdrant_client.http.models import Distance, VectorParams

from src.application.ports.cache_port import SemanticCachePort

class QdrantSemanticCache(SemanticCachePort):
    def __init__(self, qdrant_client, redis_client, cache_ttl_seconds=86400, collection_name="semantic_cache"):
        self.client = qdrant_client
        self.redis = redis_client
        self.ttl = cache_ttl_seconds
        self.collection_name = collection_name
        self._collection_ensured = False

    def _ensure_collection(self, vector_size: int):
        if self._collection_ensured:
            return
        try:
            existing = {c.name for c in self.client.get_collections().collections}
            if self.collection_name not in existing:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
            self._collection_ensured = True
        except Exception:
            pass

    async def get(
        self,
        query: str,
        query_vector: list[float],
        tenant_id: str,
        threshold: float = 0.92
    ):
        must_filters = [
            {"key": "tenant_id", "match": {"value": tenant_id}}
        ]

        now_iso = datetime.now(timezone.utc).isoformat()
        must_filters.append({
            "key": "expires_at",
            "range": {"gte": now_iso}
        })

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter={"must": must_filters},
                limit=1,
                with_payload=True
            )
        except Exception:
            # Collection might not exist yet
            return None

        if not results:
            return None

        best = results[0]

        if best.score < threshold:
            return None

        cache_id = best.payload.get("cache_id")
        if not cache_id:
            return None

        redis_key = f"retrieval_result:{cache_id}"
        cached_data = self.redis.get(redis_key)
        
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

    async def set(
        self,
        query: str,
        query_vector: list[float],
        answer: str,
        sources: list[dict],
        tenant_id: str,
        metadata: dict
    ):
        self._ensure_collection(len(query_vector))
        cache_id = str(uuid4())
        point_id = str(uuid4())

        expires_at = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + self.ttl, timezone.utc)

        redis_payload = {
            "query": query,
            "answer": answer,
            "sources": sources,
            "tenant_id": tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {})
        }
        
        redis_key = f"retrieval_result:{cache_id}"
        self.redis.setex(redis_key, self.ttl, json.dumps(redis_payload))

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                {
                    "id": point_id,
                    "vector": query_vector,
                    "payload": {
                        "cache_id": cache_id,
                        "tenant_id": tenant_id,
                        "expires_at": expires_at.isoformat()
                    }
                }
            ]
        )