import json
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from src.infrastructure.cache.qdrant_semantic_cache import QdrantSemanticCache

@pytest.fixture
def mock_qdrant():
    return MagicMock()

@pytest.fixture
def mock_redis():
    return MagicMock()

@pytest.fixture
def semantic_cache(mock_qdrant, mock_redis):
    return QdrantSemanticCache(
        qdrant_client=mock_qdrant,
        redis_client=mock_redis,
        cache_ttl_seconds=3600
    )

def create_mock_hit(score=0.98, payload=None):
    hit = MagicMock()
    hit.score = score
    hit.payload = payload or {"cache_id": "test-cache-id"}
    return hit

@pytest.mark.asyncio
async def test_semantic_cache_hit_valid(semantic_cache, mock_qdrant, mock_redis):
    mock_qdrant.search.return_value = [create_mock_hit()]
    mock_redis.get.return_value = json.dumps({
        "answer": "Test answer",
        "sources": [],
        "query": "Test query"
    })

    result = await semantic_cache.get(
        query_vector=[0.1]*1024,
        tenant_id="tenant1",
        permission_scope="public",
        corpus_version="v1",
        document_scope_hash="hash1",
        retrieval_mode="hybrid",
        query_type="stable"
    )

    assert result is not None
    assert result["answer"] == "Test answer"
    assert result["cache_hit"] is True

@pytest.mark.asyncio
async def test_semantic_cache_miss_different_permission_scope(semantic_cache, mock_qdrant):
    mock_qdrant.search.return_value = [] 
    
    result = await semantic_cache.get(
        query_vector=[0.1]*1024,
        tenant_id="tenant1",
        permission_scope="private", 
        corpus_version="v1",
        document_scope_hash="hash1",
        retrieval_mode="hybrid",
        query_type="stable"
    )

    assert result is None
    
    call_args = mock_qdrant.search.call_args[1]
    must_filters = call_args["query_filter"]["must"]
    assert any(f.get("key") == "permission_scope" and f["match"]["value"] == "private" for f in must_filters)

@pytest.mark.asyncio
async def test_semantic_cache_miss_different_document_scope_hash(semantic_cache, mock_qdrant):
    mock_qdrant.search.return_value = []
    
    result = await semantic_cache.get(
        query_vector=[0.1]*1024,
        tenant_id="tenant1",
        permission_scope="public",
        corpus_version="v1",
        document_scope_hash="different_hash", 
        retrieval_mode="hybrid",
        query_type="stable"
    )

    assert result is None
    
    call_args = mock_qdrant.search.call_args[1]
    must_filters = call_args["query_filter"]["must"]
    assert any(f.get("key") == "document_scope_hash" and f["match"]["value"] == "different_hash" for f in must_filters)

@pytest.mark.asyncio
async def test_semantic_cache_miss_different_corpus_version(semantic_cache, mock_qdrant):
    mock_qdrant.search.return_value = []
    
    result = await semantic_cache.get(
        query_vector=[0.1]*1024,
        tenant_id="tenant1",
        permission_scope="public",
        corpus_version="v2", 
        document_scope_hash="hash1",
        retrieval_mode="hybrid",
        query_type="stable"
    )

    assert result is None
    
    call_args = mock_qdrant.search.call_args[1]
    must_filters = call_args["query_filter"]["must"]
    assert any(f.get("key") == "corpus_version" and f["match"]["value"] == "v2" for f in must_filters)

@pytest.mark.asyncio
async def test_semantic_cache_redis_miss_no_crash(semantic_cache, mock_qdrant, mock_redis):
    mock_qdrant.search.return_value = [create_mock_hit()]
    
    mock_redis.get.return_value = None

    result = await semantic_cache.get(
        query_vector=[0.1]*1024,
        tenant_id="tenant1",
        permission_scope="public",
        corpus_version="v1",
        document_scope_hash="hash1",
        retrieval_mode="hybrid",
        query_type="stable"
    )

    assert result is None
    mock_redis.get.assert_called_once()

@pytest.mark.asyncio
async def test_semantic_cache_expired_cache(semantic_cache, mock_qdrant):
    mock_qdrant.search.return_value = []
    
    result = await semantic_cache.get(
        query_vector=[0.1]*1024,
        tenant_id="tenant1",
        permission_scope="public",
        corpus_version="v1",
        document_scope_hash="hash1",
        retrieval_mode="hybrid",
        query_type="stable"
    )

    assert result is None
    
    call_args = mock_qdrant.search.call_args[1]
    must_filters = call_args["query_filter"]["must"]
    
    expires_filter = next((f for f in must_filters if f.get("key") == "expires_at"), None)
    assert expires_filter is not None
    assert "gte" in expires_filter["range"]

@pytest.mark.asyncio
async def test_semantic_cache_only_stable_query_cached(semantic_cache, mock_qdrant, mock_redis):
    result_get = await semantic_cache.get(
        query_vector=[0.1]*1024,
        tenant_id="tenant1",
        permission_scope="public",
        corpus_version="v1",
        document_scope_hash="hash1",
        retrieval_mode="hybrid",
        query_type="dynamic"
    )
    assert result_get is None
    mock_qdrant.search.assert_not_called()

    await semantic_cache.set(
        query="test",
        query_vector=[0.1]*1024,
        answer="answer",
        sources=[],
        tenant_id="tenant1",
        permission_scope="public",
        corpus_version="v1",
        document_scope_hash="hash1",
        retrieval_mode="hybrid",
        query_type="dynamic" 
    )
    
    mock_redis.setex.assert_not_called()
    mock_qdrant.upsert.assert_not_called()
