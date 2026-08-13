from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.generate_answer import GenerateAnswerUseCase
from src.infrastructure.vectorstores.qdrant_store import QdrantVectorStore


def test_missing_qdrant_collection_is_an_empty_corpus() -> None:
    store = QdrantVectorStore(
        qdrant_url="http://qdrant:6333",
        collection_name="research_chunks",
        embedder=MagicMock(),
        retries=2,
    )
    store._client = MagicMock()
    store._client.query_points.side_effect = RuntimeError(
        "Unexpected Response: 404 Not Found: Collection `research_chunks` doesn't exist!"
    )

    results = store.search(
        query_vectors={"dense": [0.1], "sparse": {"indices": [], "values": []}},
        top_k=5,
    )

    assert results == []
    store._client.query_points.assert_called_once()


@pytest.mark.asyncio
async def test_empty_corpus_skips_llm_generation() -> None:
    llm = MagicMock()
    llm.multi_query_rewrite.return_value = ["question"]
    retrieve = MagicMock()
    retrieve.execute = AsyncMock(
        return_value=([], {"embedding_ms": 1.0, "retrieval_ms": 2.0})
    )
    use_case = GenerateAnswerUseCase(llm=llm, retrieve=retrieve)

    result = await use_case.execute("question")

    assert result["debug"]["retrieval_mode"] == "empty_corpus"
    assert result["citations"] == []
    llm.generate.assert_not_called()
