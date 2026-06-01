import uuid
from arq import create_pool
from arq.connections import RedisSettings
from src.infrastructure.storage.minio_storage import MinioStorage
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.infrastructure.database.models import Document, IngestionJob
from src.infrastructure.indexing.qdrant_indexer import QdrantIndexer

import hashlib
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from src.infrastructure.config.settings import get_settings
from src.api.models import IngestUploadResponse

router = APIRouter()

async def get_redis_pool():
    settings = get_settings()
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))

@router.post("/upload", response_model=IngestUploadResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    force: str = Form("false"),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF file.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
        
    name = file.filename or "upload.pdf"
    content_hash = hashlib.sha256(raw).hexdigest()
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    settings = get_settings()
    minio = MinioStorage()
    postgres = PostgresRepository()
    
    import asyncio
    # 1. Upload to MinIO
    object_name = f"raw/{content_hash[:16]}_{name}"
    try:
        await asyncio.to_thread(minio.upload_bytes, object_name, raw)
        minio_path = f"s3://{settings.minio_bucket}/{object_name}"
    except Exception as e:
        logger.error(f"Failed to upload to MinIO: {e}")
        raise HTTPException(status_code=500, detail="Storage Error")

    # 2. Save Document (uploaded) and IngestionJob (queued)
    doc_record = Document(
        id=doc_id,
        filename=name,
        minio_path=minio_path,
        status="uploaded"
    )
    await postgres.create_document(doc_record)
    
    job_record = IngestionJob(
        id=job_id,
        doc_id=doc_id,
        status="queued"
    )
    await postgres.create_ingestion_job(job_record)

    # 3. Enqueue to Arq
    redis = await get_redis_pool()
    await redis.enqueue_job("process_document", job_id)
    
    return {
        "status": "queued",
        "content_hash": content_hash,
        "doc_id": doc_id,
        "points_upserted": 0,
        "message": "Job queued for processing."
    }

@router.get("/status/{doc_id}")
async def get_task_status(doc_id: str):
    postgres = PostgresRepository()
    doc = await postgres.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": doc_id, "status": doc.status}
