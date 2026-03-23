from __future__ import annotations

from typing import Any, Dict, List

from src.infrastructure.config.settings import Settings
from src.infrastructure.indexing.qdrant_indexer import QdrantIndexer


class DocumentIndexer:
    """Infrastructure adapter for chunking + embedding + vector upsert."""

    def __init__(self, settings: Settings) -> None:
        self._indexer = QdrantIndexer(
            qdrant_url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            embed_model_name=settings.embed_model_name,
        )

    def index(self, docs: List[Dict[str, Any]]) -> None:
        chunks, _ = self._indexer.index_documents(docs)
        self._indexer.upsert_chunks(chunks)
