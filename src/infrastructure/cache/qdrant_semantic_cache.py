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

    async def get(
        self, 
        query_vector, 
        tenant_id, 
        permission_scope, 
        corpus_version, 
        document_scope_hash, 
        retrieval_mode,
        query_type,
        language="vi",
        threshold=0.95
    ):
        if query_type != "stable":
            return None

        must_filters = [
            {"key": "tenant_id", "match": {"value": tenant_id}},
            {"key": "permission_scope", "match": {"value": permission_scope}},
            {"key": "corpus_version", "match": {"value": corpus_version}},
            {"key": "document_scope_hash", "match": {"value": document_scope_hash}},
            {"key": "retrieval_mode", "match": {"value": retrieval_mode}},
            {"key": "query_type", "match": {"value": "stable"}},
            {"key": "language", "match": {"value": language}}
        ]

        now_iso = datetime.now(timezone.utc).isoformat()
        must_filters.append({
            "key": "expires_at",
            "range": {"gte": now_iso}
        })

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter={"must": must_filters},
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
        query, 
        query_vector, 
        answer, 
        sources, 
        tenant_id, 
        permission_scope, 
        corpus_version, 
        document_scope_hash, 
        retrieval_mode,
        query_type,
        language="vi",
        metadata=None
    ):
        if query_type != "stable":
            return

        metadata = metadata or {}
        cache_id = str(uuid4())
        point_id = str(uuid4())

        expires_at = datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() + self.ttl, timezone.utc)

        redis_payload = {
            "query": query,
            "answer": answer,
            "sources": sources,
            "tenant_id": tenant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **metadata
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
                        "corpus_version": corpus_version,
                        "document_scope_hash": document_scope_hash,
                        "permission_scope": permission_scope,
                        "retrieval_mode": retrieval_mode,
                        "query_type": query_type,
                        "language": language,
                        "expires_at": expires_at.isoformat()
                    }
                }
            ]
        )