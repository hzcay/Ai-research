from pathlib import Path
from typing import Any, Dict, List
from src.application.ports.document_repository_port import DocumentRepositoryPort
from src.application.ports.object_storage_port import ObjectStoragePort
from src.application.ports.parse_port import ParsePort
from src.application.ports.embedder_port import EmbedderPort
from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.document import Chunk
import asyncio
import tempfile
import os
import hashlib
from src.utils.logger import logger
from src.infrastructure.indexing.chunker import chunk_document_pages, chunk_markdown_with_tables

class ProcessDocumentUseCase:
    def __init__(
        self,
        document_repo: DocumentRepositoryPort,
        storage_port: ObjectStoragePort,
        parse_port: ParsePort,
        embedder: EmbedderPort,
        vector_store: VectorStorePort
    ):
        self._document_repo = document_repo
        self._storage = storage_port
        self._parse = parse_port
        self._embedder = embedder
        self._vector_store = vector_store

    async def execute(self, doc_id: str) -> None:
        doc = None
        try:
            doc = await self._document_repo.get_document(doc_id)
            if not doc:
                raise LookupError(f"Document {doc_id} not found")

            doc.status = "processing"
            await self._document_repo.update_document(doc)

            object_name = self._object_name_from_uri(doc.minio_path or "")
            file_bytes = await asyncio.to_thread(self._storage.get_object, object_name)

            content_hash = hashlib.sha256(file_bytes).hexdigest()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                temp_path = tmp.name

            try:
                parsed_data = await asyncio.to_thread(self._parse.parse_document, Path(temp_path))
            finally:
                os.unlink(temp_path)

            content = str(parsed_data.get("content") or "").strip()
            if not content:
                raise ValueError("Parser returned no document content")

            metadata = dict(parsed_data.get("metadata") or {})
            metadata.update({
                "content_hash": content_hash,
                "parser": parsed_data.get("source"),
                "total_pages": parsed_data.get("total_pages"),
            })
            doc.metadata_ = metadata

            markdown_object = f"parsed/{doc.id}/{content_hash}.md"
            await asyncio.to_thread(
                self._storage.upload_bytes,
                markdown_object,
                content.encode("utf-8"),
            )
            bucket_name = getattr(self._storage, "bucket_name", "ai-research")
            doc.markdown_path = f"s3://{bucket_name}/{markdown_object}"

            pages = list(parsed_data.get("pages") or [])
            has_page_text = any(
                str(page.get("text") or "").strip() for page in pages
            )
            if has_page_text:
                parent_chunks, child_chunks = chunk_document_pages(pages, doc.id)
            else:
                parent_chunks, child_chunks = chunk_markdown_with_tables(content, doc.id)
            if not parent_chunks or not child_chunks:
                raise ValueError("Chunker returned no indexable content")

            filename = doc.filename
            for chunk in [*parent_chunks, *child_chunks]:
                chunk.update({
                    "doc_id": doc.id,
                    "project_id": doc.project_id,
                    "filename": filename,
                    "content_hash": content_hash,
                    "metadata": metadata,
                })

            await asyncio.to_thread(self._vector_store.delete_document, doc.id)
            await self._document_repo.delete_chunks_by_document(doc.id)

            db_chunks = self._to_domain_chunks(
                doc.id, content_hash, parent_chunks, child_chunks
            )
            await self._document_repo.create_chunks(db_chunks)

            points_upserted = await asyncio.to_thread(
                self._vector_store.upsert_chunks, child_chunks
            )
            if points_upserted != len(child_chunks):
                raise RuntimeError(
                    f"Qdrant indexed {points_upserted}/{len(child_chunks)} child chunks"
                )
            for chunk in db_chunks:
                if chunk.chunk_type == "child":
                    chunk.embedding_status = "completed"
            await self._document_repo.create_chunks(db_chunks)

            doc.status = "completed"
            await self._document_repo.update_document(doc)
            logger.info(
                f"Completed processing {doc_id}: parents={len(parent_chunks)} "
                f"children={len(child_chunks)}"
            )

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            if doc:
                doc.status = "failed"
                await self._document_repo.update_document(doc)
            raise

    @staticmethod
    def _object_name_from_uri(uri: str) -> str:
        if not uri.startswith("s3://"):
            raise ValueError("Document has an invalid MinIO path")
        parts = uri[5:].split("/", 1)
        if len(parts) != 2 or not parts[1]:
            raise ValueError("Document has an invalid MinIO object path")
        return parts[1]

    @staticmethod
    def _to_domain_chunks(
        doc_id: str,
        content_hash: str,
        parents: List[Dict[str, Any]],
        children: List[Dict[str, Any]],
    ) -> List[Chunk]:
        output: List[Chunk] = []
        for chunk_index, chunk in enumerate([*parents, *children]):
            output.append(Chunk(
                chunk_id=str(chunk["chunk_id"]),
                doc_id=doc_id,
                parent_id=str(chunk.get("parent_id") or chunk["chunk_id"]),
                chunk_type=str(chunk.get("chunk_type") or "child"),
                text_content=str(chunk.get("text") or ""),
                chunk_index=chunk_index,
                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                token_count=int(chunk.get("token_estimate") or 0),
                content_hash=content_hash,
                section_path=chunk.get("section"),
                source_content_hash=chunk.get("source_content_hash"),
                embedding_status=(
                    "not_required" if chunk.get("chunk_type") == "parent" else "pending"
                ),
            ))
        return output
