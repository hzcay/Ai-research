from __future__ import annotations

from typing import Dict, Any, List, Optional, Protocol

from src.domain.entities.retrieval import RetrievedChunk


class VectorStorePort(Protocol):
    def search(
        self,
        query_vectors: Dict[str, Any],
        top_k: int,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        ...
