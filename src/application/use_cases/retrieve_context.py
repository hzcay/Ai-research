from __future__ import annotations

import math
import re
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
        *,
        hybrid_enabled: bool = True,
        alpha: float = 0.7,
        beta: float = 0.3,
        rerank_enabled: bool = False,
        rerank_top_n: int = 20,
        rerank_final_k: int = 5,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._hybrid_enabled = hybrid_enabled
        self._alpha = alpha
        self._beta = beta
        self._rerank_enabled = rerank_enabled
        self._rerank_top_n = rerank_top_n
        self._rerank_final_k = rerank_final_k

    def execute(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        t0 = time.perf_counter()
        query_vector = self._embedder.encode_query(query)
        cap = max(top_k, self._rerank_top_n)
        semantic = self._vector_store.search(
            query_vector=query_vector,
            top_k=cap,
            document_id=document_id,
        )
        if not self._hybrid_enabled:
            out = semantic[:top_k]
            logger.bind(stage="retrieve", strategy="semantic_only").info(
                f"query='{query}' doc={document_id!r} results={len(out)} latency_ms={_ms(t0)}"
            )
            return out

        lexical = self._vector_store.keyword_search(
            query_text=query,
            top_k=cap,
            document_id=document_id,
        )
        fused = _rrf_fuse(semantic, lexical)
        boosted = _hybrid_boost(fused, query=query, alpha=self._alpha, beta=self._beta)

        if self._rerank_enabled:
            boosted = _keyword_rerank(boosted[: self._rerank_top_n], query=query, final_k=min(top_k, self._rerank_final_k))
        out = boosted[:top_k]
        logger.bind(stage="retrieve", strategy="hybrid").info(
            f"query='{query}' doc={document_id!r} semantic={len(semantic)} lexical={len(lexical)} "
            f"results={len(out)} latency_ms={_ms(t0)}"
        )
        return out


def _rrf_fuse(a: List[RetrievedChunk], b: List[RetrievedChunk], k: int = 60) -> List[RetrievedChunk]:
    by_id: dict[str, RetrievedChunk] = {}
    score: dict[str, float] = {}
    for rank, c in enumerate(a, start=1):
        by_id[c.id] = c
        score[c.id] = score.get(c.id, 0.0) + 1.0 / (k + rank)
    for rank, c in enumerate(b, start=1):
        by_id[c.id] = by_id.get(c.id, c)
        score[c.id] = score.get(c.id, 0.0) + 1.0 / (k + rank)
    ordered_ids = sorted(score.keys(), key=lambda cid: score[cid], reverse=True)
    return [by_id[cid] for cid in ordered_ids]


def _hybrid_boost(chunks: List[RetrievedChunk], query: str, alpha: float, beta: float) -> List[RetrievedChunk]:
    q_terms = _tokenize(query)
    rescored: List[tuple[float, RetrievedChunk]] = []
    for c in chunks:
        sem = float(c.score or 0.0)
        key = _keyword_overlap_score(q_terms, _tokenize(c.text))
        final = alpha * sem + beta * key
        rescored.append((final, c))
    rescored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in rescored]

def _keyword_rerank(chunks: List[RetrievedChunk], query: str, final_k: int) -> List[RetrievedChunk]:
    q_terms = _tokenize(query)
    scored: List[tuple[float, RetrievedChunk]] = []
    for c in chunks:
        overlap = _keyword_overlap_score(q_terms, _tokenize(c.text))
        len_penalty = math.log(max(10, len(c.text))) / 10.0
        scored.append((overlap - len_penalty * 0.01 + float(c.score or 0.0) * 0.1, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:final_k]]

def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9_\-]{2,}", text.lower())}


def _keyword_overlap_score(query_terms: set[str], doc_terms: set[str]) -> float:
    if not query_terms or not doc_terms:
        return 0.0
    inter = len(query_terms.intersection(doc_terms))
    if inter == 0:
        return 0.0
    return inter / len(query_terms)


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
