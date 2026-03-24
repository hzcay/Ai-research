from __future__ import annotations

from typing import List, Protocol

from src.domain.entities.retrieval import RetrievedChunk


class VectorStorePort(Protocol):
    def search(self, query_vector: List[float], top_k: int) -> List[RetrievedChunk]:
        ...

    def keyword_search(self, query_text: str, top_k: int) -> List[RetrievedChunk]:
        ...
