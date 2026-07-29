from __future__ import annotations

import time
from typing import List, Optional

from src.application.ports.embedder_port import EmbedderPort
from src.application.ports.vector_store_port import VectorStorePort
from src.application.ports.reranker_port import RerankerPort
from src.domain.entities.retrieval import RetrievedChunk
from src.application.ports.cache_port import ChunkCachePort
from src.application.ports.document_repository_port import DocumentRepositoryPort
from src.utils.logger import logger
import asyncio
import json
from pathlib import Path

class RetrieveContextUseCase:
    def __init__(
        self,
        embedder: EmbedderPort,
        vector_store: VectorStorePort,
        chunk_cache: ChunkCachePort,
        document_repo: DocumentRepositoryPort,
        reranker: Optional[RerankerPort] = None,
        **kwargs
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._chunk_cache = chunk_cache
        self._document_repo = document_repo
        self._reranker = reranker
        self._rerank_enabled = kwargs.get("rerank_enabled", False)
        self._rerank_top_n = kwargs.get("rerank_top_n", 20)
        self._rerank_final_k = kwargs.get("rerank_final_k", 5)

    async def execute(
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
        
        actual_top_k = self._rerank_top_n if (self._rerank_enabled and self._reranker) else top_k
        
        out = self._vector_store.search(
            query_vectors=query_vectors,
            top_k=actual_top_k,
            document_id=document_id,
        )
        
        parent_ids = []
        for chunk in out:
            parent_id = chunk.metadata.get("parent_id")
            if parent_id and parent_id not in parent_ids:
                parent_ids.append(parent_id)

        if not parent_ids:
            parent_ids = [chunk.id for chunk in out]
            
        cached_texts = self._chunk_cache.get_multiple_chunks(parent_ids)
        
        missing_ids = [pid for pid in parent_ids if pid not in cached_texts]
        if missing_ids:
            try:
                db_chunks = await self._document_repo.get_chunks_by_ids(missing_ids)
                for db_chunk in db_chunks:
                    cached_texts[db_chunk.chunk_id] = db_chunk.text_content
                    self._chunk_cache.set_chunk_text(db_chunk.chunk_id, db_chunk.text_content)
            except Exception as e:
                logger.error(f"Postgres hydration failed: {e}")
                raise RuntimeError("Document content is temporarily unavailable") from e
                
        
        parent_out = []
        for pid in parent_ids:
            text = cached_texts.get(pid, "")
            if not text:
                continue
                
            matching = [
                c for c in out
                if c.metadata.get("parent_id") == pid or c.id == pid
            ]
            best_match = max(
                matching, key=lambda c: float(c.score or 0.0), default=None
            )
            best_score = float(best_match.score or 0.0) if best_match else 0.0
            source_metadata = dict(best_match.metadata) if best_match else {}
            source_metadata.update({
                "is_parent": True,
                "source_block_id": pid,
                "page": source_metadata.get("page_start"),
            })
            
            parent_out.append(
                RetrievedChunk(
                    id=pid,
                    doc_id=best_match.doc_id if best_match else "",
                    score=best_score,
                    text=text,
                    page_start=source_metadata.get("page_start"),
                    page_end=source_metadata.get("page_end"),
                    metadata=source_metadata,
                )
            )
            
        rerank_ms = 0.0

        if self._rerank_enabled and self._reranker and parent_out:
            start_rerank = time.perf_counter()
            texts = [c.text for c in parent_out]
            try:
                scores = self._reranker.rerank(query, texts)
                for c, s in zip(parent_out, scores):
                    c.score = s

                parent_out.sort(key=lambda x: x.score, reverse=True)
                parent_out = parent_out[:self._rerank_final_k]
            except Exception as e:
                logger.error(f"Reranking failed: {e}")
                parent_out = parent_out[:top_k]
                
            rerank_ms = (time.perf_counter() - start_rerank) * 1000
        else:
            
            parent_out = parent_out[:top_k]

        final_out = []
        total_tokens = 0
        MAX_CONTEXT_TOKENS = 6000 
        for c in parent_out:
            est_tokens = len(c.text.split()) * 1.3
            if total_tokens + est_tokens > MAX_CONTEXT_TOKENS:
                continue
            total_tokens += est_tokens
            final_out.append(c)
            
        out = final_out
        
        retrieval_ms = (time.perf_counter() - start_retrieval) * 1000

        logger.bind(stage="retrieve", strategy="true_hybrid").info(
            f"query='{query}' doc={document_id!r} results={len(out)} latency_ms={_ms(t0)} cache_miss={len(missing_ids)}"
        )
        
        metrics = {
            "embedding_ms": embedding_ms,
            "retrieval_ms": retrieval_ms,
            "rerank_ms": rerank_ms
        }
        
        try:
            debug_dir = Path("data/debug")
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_file = debug_dir / "retrieval_debug.json"
            debug_data = {
                "query": query,
                "top_k": top_k,
                "document_id": document_id,
                "missing_ids": missing_ids,
                "metrics": metrics,
                "results": [
                    {
                        "id": c.id,
                        "doc_id": c.doc_id,
                        "score": c.score,
                        "text": c.text,
                        "metadata": c.metadata
                    } for c in out
                ]
            }
            debug_file.write_text(json.dumps(debug_data, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write retrieval_debug.json: {e}")
        
        return out, metrics

def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
