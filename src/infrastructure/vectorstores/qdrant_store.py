from __future__ import annotations

from typing import Any, List

import qdrant_client

from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.retrieval import RetrievedChunk


class QdrantVectorStore(VectorStorePort):
    def __init__(self, qdrant_url: str, collection_name: str) -> None:
        self._client = qdrant_client.QdrantClient(url=qdrant_url)
        self._collection_name = collection_name

    def search(self, query_vector: List[float], top_k: int) -> List[RetrievedChunk]:
        hits = self._query(query_vector=query_vector, top_k=top_k)
        output: List[RetrievedChunk] = []
        for hit in hits:
            payload = getattr(hit, "payload", None) or {}
            text = payload.get("text") or payload.get("content") or ""
            output.append(
                RetrievedChunk(
                    id=str(getattr(hit, "id", "")),
                    score=getattr(hit, "score", None),
                    text=text,
                    metadata=payload.get("metadata", {}),
                    payload=payload,
                )
            )
        return output

    def _query(self, query_vector: List[float], top_k: int) -> List[Any]:
        if hasattr(self._client, "query_points"):
            response = self._client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )
            return list(response.points)

        if hasattr(self._client, "search"):
            return self._client.search(
                collection_name=self._collection_name,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True,
            )

        raise AttributeError("Qdrant client has no supported search method.")
