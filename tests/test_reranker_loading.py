import pytest
from unittest.mock import MagicMock, patch
from src.infrastructure.embeddings.bge_reranker import BgeReranker
from src.application.use_cases.retrieve_context import RetrieveContextUseCase
from src.domain.entities.retrieval import RetrievedChunk

def test_bge_reranker_lazy_loading():
    with patch('src.infrastructure.embeddings.bge_reranker.logger'):
        reranker = BgeReranker()
        assert reranker._model is None, "Model should not be loaded on init"

        mock_flag_module = MagicMock()
        with patch.dict('sys.modules', {'FlagEmbedding': mock_flag_module}):
            mock_flag_reranker_class = MagicMock()
            mock_model_instance = MagicMock()
            mock_model_instance.compute_score.return_value = [0.9]
            mock_flag_reranker_class.return_value = mock_model_instance
            mock_flag_module.FlagReranker = mock_flag_reranker_class
            
            scores = reranker.rerank("query", ["text"])
                
            assert reranker._model is not None
            mock_flag_reranker_class.assert_called_once_with("BAAI/bge-reranker-base", use_fp16=True)
            mock_model_instance.compute_score.assert_called_once()
            assert scores == [0.9]


@pytest.mark.asyncio
async def test_retrieve_context_skips_reranker_when_disabled():
    mock_embedder = MagicMock()
    mock_embedder.encode_query.return_value = {"dense": [0.1]}
    
    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = [
        RetrievedChunk(id="1", doc_id="doc1", score=0.5, text="vector text", metadata={"parent_id": "parent1"})
    ]
    
    mock_redis = MagicMock()
    mock_redis.get_multiple_chunks.return_value = {"parent1": "parent text"}
    
    mock_postgres = MagicMock()
    
    mock_reranker = MagicMock()
    
    use_case = RetrieveContextUseCase(
        embedder=mock_embedder,
        vector_store=mock_vector_store,
        chunk_cache=mock_redis,
        document_repo=mock_postgres,
        reranker=mock_reranker,
        rerank_enabled=False
    )
    
    out, metrics = await use_case.execute(query="test", top_k=5)
    
    mock_reranker.rerank.assert_not_called()
    
    assert len(out) == 1
    assert out[0].id == "parent1"
    assert out[0].text == "parent text"
