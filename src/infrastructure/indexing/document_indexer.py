from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List

from src.infrastructure.config.settings import Settings
from src.infrastructure.indexing.qdrant_indexer import QdrantIndexer
from src.infrastructure.parsing.docling_parser import parse_research_paper


def _safe_filename(name: str) -> str:
    base = Path(name).name
    s = re.sub(r"[^\w.\-]", "_", base).strip("._") or "upload"
    return s[:200]


class DocumentIndexer:
    """Infrastructure adapter for chunking + embedding + vector upsert."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._indexer = QdrantIndexer(
            qdrant_url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            embed_model_name=settings.embed_model_name,
        )

    def index(self, docs: List[Dict[str, Any]]) -> None:
        chunks, _ = self._indexer.index_documents(docs)
        self._indexer.upsert_chunks(chunks)

    def ingest_pdf_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        *,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Parse one PDF from memory, chunk/embed/upsert. Dedupe by SHA-256 of raw bytes unless force."""
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        if not force:
            existing = self._indexer.find_doc_id_by_content_hash(content_hash)
            if existing:
                return {
                    "status": "duplicate",
                    "content_hash": content_hash,
                    "doc_id": existing,
                    "points_upserted": 0,
                    "message": "Same PDF bytes already indexed.",
                }

        doc_id = hashlib.sha1(content_hash.encode("ascii")).hexdigest()[:12]
        upload_root = Path(self._settings.upload_dir)
        upload_root.mkdir(parents=True, exist_ok=True)
        safe = _safe_filename(filename)
        saved = upload_root / f"{content_hash[:16]}_{safe}"
        saved.write_bytes(file_bytes)

        parsed = parse_research_paper(saved)
        meta = dict(parsed.get("metadata") or {})
        meta["content_hash"] = content_hash
        meta["upload_filename"] = filename

        doc = {
            "filename": str(parsed.get("filename") or safe),
            "content": str(parsed.get("content") or ""),
            "metadata": meta,
            "content_hash": content_hash,
            "doc_id": doc_id,
        }
        chunks, _ = self._indexer.index_documents([doc])
        n = self._indexer.upsert_chunks(chunks)
        return {
            "status": "indexed",
            "content_hash": content_hash,
            "doc_id": doc_id,
            "points_upserted": n,
            "saved_path": str(saved),
        }
