from __future__ import annotations

import time
from typing import List, Optional

from src.application.ports.embedder_port import EmbedderPort
from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.retrieval import RetrievedChunk
from src.utils.logger import logger


class RetrieveContextUseCase:
    def __init__(
        self,
        embedder: EmbedderPort,
        vector_store: VectorStorePort,
        **kwargs
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store

    def execute(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> tuple[List[RetrievedChunk], dict[str, float]]:
        t0 = time.perf_counter()
        
        start_embed = time.perf_counter()
        query_vectors = self._embedder.encode_query(query)
        embedding_ms = (time.perf_counter() - start_embed) * 1000
        
        start_retrieval = time.perf_counter()
        out = self._vector_store.search(
            query_vectors=query_vectors,
            top_k=top_k,
            document_id=document_id,
        )
        retrieval_ms = (time.perf_counter() - start_retrieval) * 1000

        logger.bind(stage="retrieve", strategy="true_hybrid").info(
            f"query='{query}' doc={document_id!r} results={len(out)} latency_ms={_ms(t0)}"
        )
        
        metrics = {
            "embedding_ms": embedding_ms,
            "retrieval_ms": retrieval_ms
        }
        
        return out, metrics

def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
