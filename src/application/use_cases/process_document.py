from typing import Optional
from src.application.ports.document_repository_port import DocumentRepositoryPort
from src.application.ports.object_storage_port import ObjectStoragePort
from src.application.ports.parse_port import ParsePort
from src.application.ports.embedder_port import EmbedderPort
from src.application.ports.vector_store_port import VectorStorePort
from src.domain.entities.document import Chunk
import tempfile
import os
import hashlib
from src.utils.logger import logger

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
        try:
            doc = await self._document_repo.get_document(doc_id)
            if not doc:
                logger.error(f"Document {doc_id} not found.")
                return

            doc.status = "processing"
            await self._document_repo.update_document(doc)

            object_name = "/".join(doc.minio_path.split("/")[3:])
            file_bytes = self._storage.get_object(object_name)

            content_hash = hashlib.sha256(file_bytes).hexdigest()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                temp_path = tmp.name

            try:
                parsed_data = self._parse.parse_document(temp_path)
            finally:
                os.unlink(temp_path)

            logger.info(f"Successfully parsed {doc.filename}")
            
            doc.status = "completed"
            await self._document_repo.update_document(doc)
            logger.info(f"Completed processing {doc_id}")

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {e}")
            doc = await self._document_repo.get_document(doc_id)
            if doc:
                doc.status = "failed"
                await self._document_repo.update_document(doc)
            raise e
