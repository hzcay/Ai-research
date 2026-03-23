from __future__ import annotations

from typing import List

from src.application.ports.embedder_port import EmbedderPort
from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.retrieval import RetrievedChunk


class RetrieveContextUseCase:
    def __init__(self, embedder: EmbedderPort, vector_store: VectorStorePort) -> None:
        self._embedder = embedder
        self._vector_store = vector_store

    def execute(self, query: str, top_k: int = 2) -> List[RetrievedChunk]:
        query_vector = self._embedder.encode_query(query)
        return self._vector_store.search(query_vector=query_vector, top_k=top_k)
