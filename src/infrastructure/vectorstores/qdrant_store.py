from __future__ import annotations

import math
import re
import time
from typing import Any, List

import qdrant_client

from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.retrieval import RetrievedChunk


class QdrantVectorStore(VectorStorePort):
    def __init__(
        self,
        qdrant_url: str,
        collection_name: str,
        timeout_s: float = 10.0,
        retries: int = 2,
        lexical_candidate_limit: int = 1000,
    ) -> None:
        self._client = qdrant_client.QdrantClient(url=qdrant_url, timeout=timeout_s)
        self._collection_name = collection_name
        self._retries = max(0, retries)
        self._lexical_candidate_limit = max(10, lexical_candidate_limit)

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
        for attempt in range(self._retries + 1):
            try:
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
            except Exception:
                if attempt >= self._retries:
                    raise
                time.sleep(0.2 * math.pow(2, attempt))
        return []

    def keyword_search(self, query_text: str, top_k: int) -> List[RetrievedChunk]:
        terms = _tokenize(query_text)
        if not terms:
            return []

        points = self._scroll_payloads(limit=self._lexical_candidate_limit)
        scored: List[tuple[float, Any]] = []
        for p in points:
            payload = getattr(p, "payload", None) or {}
            text = str(payload.get("text") or payload.get("content") or "")
            if not text:
                continue
            score = _keyword_overlap_score(terms, _tokenize(text))
            if score > 0:
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        output: List[RetrievedChunk] = []
        for score, p in scored[:top_k]:
            payload = getattr(p, "payload", None) or {}
            text = payload.get("text") or payload.get("content") or ""
            output.append(
                RetrievedChunk(
                    id=str(getattr(p, "id", "")),
                    score=score,
                    text=text,
                    metadata=payload.get("metadata", {}),
                    payload=payload,
                )
            )
        return output

    def _scroll_payloads(self, limit: int) -> List[Any]:
        all_points: List[Any] = []
        offset = None
        remaining = limit
        while remaining > 0:
            batch_size = min(128, remaining)
            for attempt in range(self._retries + 1):
                try:
                    points, next_offset = self._client.scroll(
                        collection_name=self._collection_name,
                        limit=batch_size,
                        with_payload=True,
                        with_vectors=False,
                        offset=offset,
                    )
                    all_points.extend(points)
                    offset = next_offset
                    remaining -= len(points)
                    break
                except Exception:
                    if attempt >= self._retries:
                        raise
                    time.sleep(0.2 * math.pow(2, attempt))
            if offset is None:
                break
        return all_points


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9_\-]{2,}", text.lower())}


def _keyword_overlap_score(query_terms: set[str], doc_terms: set[str]) -> float:
    if not query_terms or not doc_terms:
        return 0.0
    inter = len(query_terms.intersection(doc_terms))
    if inter == 0:
        return 0.0
    return inter / len(query_terms)
