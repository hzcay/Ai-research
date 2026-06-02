from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List

from src.infrastructure.config.settings import Settings
from src.infrastructure.indexing.qdrant_indexer import QdrantIndexer
from src.infrastructure.parsing.docling_parser import parse_research_paper
from src.infrastructure.storage.minio_storage import MinioStorage
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.infrastructure.database.models import Document, Chunk
import asyncio
import uuid
import tempfile
import os
from src.utils.logger import logger


def _safe_filename(name: str) -> str:
    base = Path(name).name
    s = re.sub(r"[^\w.\-]", "_", base).strip("._") or "upload"
    return s[:200]


class DocumentIndexer:
    """Infrastructure adapter for chunking + embedding + vector upsert."""

    def __init__(
        self, 
        settings: Settings,
        minio_storage: MinioStorage,
        postgres_repo: PostgresRepository
    ) -> None:
        self._settings = settings
        self._minio = minio_storage
        self._postgres = postgres_repo
        self._indexer = QdrantIndexer(
            qdrant_url=settings.qdrant_url,
            collection_name=settings.qdrant_collection,
            embed_model_name=settings.embed_model_name,
        )

    def index(self, docs: List[Dict[str, Any]]) -> None:
        parent_chunks, child_chunks, _ = self._indexer.index_documents(docs)
        self._indexer.upsert_chunks(child_chunks)

    async def ingest_pdf_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        *,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Async Ingestion Pipeline: MinIO -> Postgres -> Qdrant"""
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        
        doc_id = str(uuid.uuid4())
        safe = _safe_filename(filename)
        
        object_name = f"raw/{content_hash[:16]}_{safe}"
        try:
            await asyncio.to_thread(self._minio.upload_bytes, object_name, file_bytes)
            minio_path = f"s3://{self._settings.minio_bucket}/{object_name}"
        except Exception as e:
            logger.error(f"Failed to upload {filename} to MinIO: {e}")
            raise

        doc_record = Document(
            id=doc_id,
            filename=safe,
            minio_path=minio_path,
            status="processing"
        )
        await self._postgres.create_document(doc_record)

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                temp_path = Path(tmp.name)
                
            parsed = await asyncio.to_thread(parse_research_paper, temp_path)
            os.unlink(temp_path)
            
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
            
            parent_chunks, child_chunks, _ = await asyncio.to_thread(self._indexer.index_documents, [doc])
            
            stem = Path(filename).stem
            debug_dir = Path("data/debug") / stem
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            raw_path = debug_dir / "raw_content.md"
            raw_path.write_text(str(parsed.get("raw_content", "")), encoding="utf-8")
            
            proc_path = debug_dir / "cleaned_content.md"
            proc_path.write_text(str(parsed.get("content", "")), encoding="utf-8")
            
            import json
            audit_path = debug_dir / "chunks_audit.json"
            audit_data = {
                "parent_chunks": parent_chunks,
                "child_chunks": child_chunks
            }
            audit_path.write_text(json.dumps(audit_data, indent=2, default=str), encoding="utf-8")
            
            db_chunks = []
            
            for i, p in enumerate(parent_chunks):
                db_chunks.append(Chunk(
                    chunk_id=p["chunk_id"],
                    parent_id=p["parent_id"],
                    chunk_type="parent",
                    doc_id=doc_id,
                    text_content=str(p.get("text", "")),
                    chunk_index=i,
                    page_start=p.get("page_start", None),
                    page_end=p.get("page_end", None),
                    token_count=p.get("token_estimate", 0),
                    content_hash=content_hash,
                    embedding_status="completed"
                ))
                
            for i, c in enumerate(child_chunks):
                db_chunks.append(Chunk(
                    chunk_id=c["chunk_id"],
                    parent_id=c["parent_id"],
                    chunk_type="child",
                    doc_id=doc_id,
                    text_content=str(c.get("text", "")),
                    chunk_index=i,
                    page_start=c.get("page_start", None),
                    page_end=c.get("page_end", None),
                    token_count=c.get("token_estimate", 0),
                    content_hash=content_hash,
                    embedding_status="completed"
                ))
            
            await self._postgres.create_chunks(db_chunks)
            
            n = await asyncio.to_thread(self._indexer.upsert_chunks, child_chunks)
            
            doc_record.status = "completed"
            await self._postgres.update_document(doc_record) 
            
            return {
                "status": "indexed",
                "content_hash": content_hash,
                "doc_id": doc_id,
                "points_upserted": n,
                "minio_path": minio_path,
            }
            
        except Exception as e:
            logger.error(f"Ingestion pipeline failed for doc_id {doc_id}: {e}")
            doc_record.status = "failed"
            await self._postgres.update_document(doc_record)
            raise
