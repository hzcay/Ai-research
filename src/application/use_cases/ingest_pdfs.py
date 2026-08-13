from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
import asyncio
import re

from src.application.ports.object_storage_port import ObjectStoragePort
from src.application.ports.document_repository_port import DocumentRepositoryPort
from src.application.ports.task_queue_port import TaskQueuePort
from src.domain.entities.document import Document, IngestionJob
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

    async def execute(
        self,
        file_bytes: bytes,
        filename: str,
        *,
        force: bool = False,
        project_id: str | None = None,
    ) -> dict:
        try:
            content_hash = hashlib.sha256(file_bytes).hexdigest()
            existing = await self._repo.get_document_by_content_hash(
                content_hash, project_id=project_id
            )
            if existing and not force:
                return {
                    "status": (
                        "duplicate" if existing.status == "completed" else existing.status
                    ),
                    "content_hash": content_hash,
                    "doc_id": existing.id,
                    "message": f"Document already exists with status {existing.status}.",
                }

            doc_id = existing.id if existing else str(uuid.uuid4())
            
            safe_filename = re.sub(
                r"[^\w.\-]", "_", Path(filename).name
            ).strip("._") or "upload.pdf"
            object_name = f"raw/{content_hash[:16]}_{safe_filename}"
            await asyncio.to_thread(self._storage.upload_bytes, object_name, file_bytes)
            bucket_name = getattr(self._storage, "bucket_name", "ai-research")
            minio_path = f"s3://{bucket_name}/{object_name}"
            
            if existing:
                doc_record = existing
                doc_record.filename = safe_filename
                doc_record.minio_path = minio_path
                doc_record.status = "queued"
                doc_record.content_hash = content_hash
                doc_record.project_id = project_id or doc_record.project_id
                await self._repo.update_document(doc_record)
                ingestion_job = await self._repo.get_ingestion_job_by_doc_id(doc_id)
                if ingestion_job is None:
                    ingestion_job = IngestionJob(id=str(uuid.uuid4()), doc_id=doc_id)
                    await self._repo.create_ingestion_job(ingestion_job)
                else:
                    ingestion_job.status = "pending_enqueue"
                    ingestion_job.error_message = None
                    ingestion_job.queue_job_id = None
                    await self._repo.update_ingestion_job(ingestion_job)
            else:
                doc_record = Document(
                    id=doc_id,
                    filename=safe_filename,
                    minio_path=minio_path,
                    status="queued",
                    content_hash=content_hash,
                    project_id=project_id,
                )
                ingestion_job = IngestionJob(
                    id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    status="pending_enqueue",
                )
                await self._repo.create_document_with_job(doc_record, ingestion_job)

            try:
                queue_job_id = f"ingest:{doc_id}:{uuid.uuid4()}"
                await self._task_queue.enqueue_job(
                    "process_document", doc_id, _job_id=queue_job_id
                )
                ingestion_job.status = "queued"
                ingestion_job.error_message = None
                ingestion_job.queue_job_id = queue_job_id
            except Exception as enqueue_error:
                ingestion_job.status = "enqueue_failed"
                ingestion_job.error_message = str(enqueue_error)[:1000]
                logger.error(
                    f"Persisted document {doc_id}, but queueing failed: {enqueue_error}"
                )
            await self._repo.update_ingestion_job(ingestion_job)
            logger.info(f"Enqueued document {filename} with ID {doc_id}")
            
            return {
                "status": doc_record.status,
                "content_hash": content_hash,
                "doc_id": doc_id,
                "message": (
                    "Job queued for processing."
                    if ingestion_job.status == "queued"
                    else "Upload saved; processing will be retried automatically."
                ),
            }
            
        except Exception as e:
            logger.error(f"Failed to enqueue {filename}: {e}")
            raise
