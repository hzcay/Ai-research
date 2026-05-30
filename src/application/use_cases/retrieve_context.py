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
        
        # Hydrate text from Cache or DB
        chunk_ids = [chunk.id for chunk in out]
        cached_texts = self._redis_cache.get_multiple_chunks(chunk_ids)
        
        missing_ids = [cid for cid in chunk_ids if cid not in cached_texts]
        if missing_ids:
            try:
                db_chunks = asyncio.run(self._postgres_repo.get_chunks_by_ids(missing_ids))
                for db_chunk in db_chunks:
                    cached_texts[db_chunk.chunk_id] = db_chunk.text_content
                    self._redis_cache.set_chunk_text(db_chunk.chunk_id, db_chunk.text_content)
            except Exception as e:
                logger.error(f"Postgres hydration failed: {e}")
                
        for chunk in out:
            chunk.text = cached_texts.get(chunk.id, "")
        
        retrieval_ms = (time.perf_counter() - start_retrieval) * 1000

        logger.bind(stage="retrieve", strategy="true_hybrid").info(
            f"query='{query}' doc={document_id!r} results={len(out)} latency_ms={_ms(t0)} cache_miss={len(missing_ids)}"
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
