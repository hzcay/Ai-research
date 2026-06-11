from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import List
import asyncio

from src.application.ports.object_storage_port import ObjectStoragePort
from src.application.ports.document_repository_port import DocumentRepositoryPort
from src.application.ports.task_queue_port import TaskQueuePort
from src.domain.entities.document import Document
from src.utils.logger import logger

class IngestPdfsUseCase:
    def __init__(
        self, 
        storage_port: ObjectStoragePort,
        repo_port: DocumentRepositoryPort,
        task_queue: TaskQueuePort
    ) -> None:
        self._storage = storage_port
        self._repo = repo_port
        self._task_queue = task_queue

    async def execute(self, file_bytes: bytes, filename: str) -> dict:
        try:
            content_hash = hashlib.sha256(file_bytes).hexdigest()
            doc_id = str(uuid.uuid4())
            
            safe_filename = filename.replace(" ", "_")
            object_name = f"raw/{content_hash[:16]}_{safe_filename}"
            await asyncio.to_thread(self._storage.upload_bytes, object_name, file_bytes)
            minio_path = f"s3://bucket/{object_name}" 
            
            doc_record = Document(
                id=doc_id,
                filename=filename,
                minio_path=minio_path,
                status="queued"
            )
            await self._repo.create_document(doc_record)
                
            await self._task_queue.enqueue_job("process_document", doc_id)
            logger.info(f"Enqueued document {filename} with ID {doc_id}")
            
            return {
                "status": "queued",
                "content_hash": content_hash,
                "doc_id": doc_id,
                "message": "Job queued for processing."
            }
            
        except Exception as e:
            logger.error(f"Failed to enqueue {filename}: {e}")
            raise e
