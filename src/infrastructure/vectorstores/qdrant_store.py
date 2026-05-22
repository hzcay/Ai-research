from __future__ import annotations

import math
import re
import time
from typing import Any, List, Optional

import qdrant_client
from qdrant_client import models

from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.retrieval import RetrievedChunk


def _doc_id_filter(document_id: Optional[str]) -> Optional[models.Filter]:
    if not document_id:
        return None
    return models.Filter(
        must=[
            models.FieldCondition(
                key="doc_id",
                match=models.MatchValue(value=document_id),
            )
        ]
    )


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

    def search(
        self,
        query_vector: List[float],
        top_k: int,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        hits = self._query(query_vector=query_vector, top_k=top_k, document_id=document_id)
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

    def _query(
        self,
        query_vector: List[float],
        top_k: int,
        document_id: Optional[str] = None,
    ) -> List[Any]:
        qf = _doc_id_filter(document_id)
        for attempt in range(self._retries + 1):
            try:
                if hasattr(self._client, "query_points"):
                    qp: dict[str, Any] = {
                        "collection_name": self._collection_name,
                        "query": query_vector,
                        "limit": top_k,
                        "with_payload": True,
                    }
                    if qf is not None:
                        qp["query_filter"] = qf
                    response = self._client.query_points(**qp)
                    return list(response.points)

                if hasattr(self._client, "search"):
                    sp: dict[str, Any] = {
                        "collection_name": self._collection_name,
                        "query_vector": query_vector,
                        "limit": top_k,
                        "with_payload": True,
                    }
                    if qf is not None:
                        sp["query_filter"] = qf
                    return self._client.search(**sp)

                raise AttributeError("Qdrant client has no supported search method.")
            except Exception as e:
                if "Not found: Collection" in str(e):
                    return []
                if attempt >= self._retries:
                    raise
                time.sleep(0.2 * math.pow(2, attempt))
        return []

    def keyword_search(
        self,
        query_text: str,
        top_k: int,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        terms = _tokenize(query_text)
        if not terms:
            return []

        points = self._scroll_payloads(
            limit=self._lexical_candidate_limit,
            document_id=document_id,
        )
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

    def _scroll_payloads(self, limit: int, document_id: Optional[str] = None) -> List[Any]:
        all_points: List[Any] = []
        offset = None
        remaining = limit
        sf = _doc_id_filter(document_id)
        while remaining > 0:
            batch_size = min(128, remaining)
            for attempt in range(self._retries + 1):
                try:
                    sk: dict[str, Any] = {
                        "collection_name": self._collection_name,
                        "limit": batch_size,
                        "with_payload": True,
                        "with_vectors": False,
                        "offset": offset,
                    }
                    if sf is not None:
                        sk["scroll_filter"] = sf
                    points, next_offset = self._client.scroll(**sk)
                    all_points.extend(points)
                    offset = next_offset
                    remaining -= len(points)
                    break
                except Exception as e:
                    if "Not found: Collection" in str(e):
                        return []
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
