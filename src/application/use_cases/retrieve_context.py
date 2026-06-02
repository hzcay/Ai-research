from __future__ import annotations

import time
from typing import List, Optional

from src.application.ports.embedder_port import EmbedderPort
from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.retrieval import RetrievedChunk
from src.infrastructure.cache.redis_hot_cache import RedisHotCache
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.utils.logger import logger
import asyncio
import json
from pathlib import Path

class RetrieveContextUseCase:
    def __init__(
        self,
        embedder: EmbedderPort,
        vector_store: VectorStorePort,
        redis_cache: RedisHotCache,
        postgres_repo: PostgresRepository,
        **kwargs
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._redis_cache = redis_cache
        self._postgres_repo = postgres_repo

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
        out = self._vector_store.search(
            query_vectors=query_vectors,
            top_k=top_k,
            document_id=document_id,
        )
        
        parent_ids = []
        for chunk in out:
            parent_id = chunk.metadata.get("parent_id")
            if parent_id and parent_id not in parent_ids:
                parent_ids.append(parent_id)

        if not parent_ids:
            parent_ids = [chunk.id for chunk in out]
            
        cached_texts = self._redis_cache.get_multiple_chunks(parent_ids)
        
        missing_ids = [pid for pid in parent_ids if pid not in cached_texts]
        if missing_ids:
            try:
                db_chunks = await self._postgres_repo.get_chunks_by_ids(missing_ids)
                for db_chunk in db_chunks:
                    cached_texts[db_chunk.chunk_id] = db_chunk.text_content
                    self._redis_cache.set_chunk_text(db_chunk.chunk_id, db_chunk.text_content)
            except Exception as e:
                logger.error(f"Postgres hydration failed: {e}")
                
        
        parent_out = []
        total_tokens = 0
        MAX_CONTEXT_TOKENS = 6000 
        
        for pid in parent_ids:
            text = cached_texts.get(pid, "")
            if not text:
                continue
                

            est_tokens = len(text.split()) * 1.3
            if total_tokens + est_tokens > MAX_CONTEXT_TOKENS:
                break
                
            total_tokens += est_tokens
            
            best_score = max([c.score for c in out if c.metadata.get("parent_id") == pid or c.id == pid] + [0.0])
            
            parent_out.append(
                RetrievedChunk(
                    id=pid,
                    doc_id=out[0].doc_id if out else "",
                    score=best_score,
                    text=text,
                    page_start=None,
                    metadata={"is_parent": True}
                )
            )
            
        out = parent_out
        
        retrieval_ms = (time.perf_counter() - start_retrieval) * 1000

        logger.bind(stage="retrieve", strategy="true_hybrid").info(
            f"query='{query}' doc={document_id!r} results={len(out)} latency_ms={_ms(t0)} cache_miss={len(missing_ids)}"
        )
        
        metrics = {
            "embedding_ms": embedding_ms,
            "retrieval_ms": retrieval_ms
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


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
