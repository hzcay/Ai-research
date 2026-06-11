import uuid
from arq import create_pool
from arq.connections import RedisSettings
from src.infrastructure.storage.minio_storage import MinioStorage
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.domain.entities.document import Document, IngestionJob
from src.infrastructure.indexing.qdrant_indexer import QdrantIndexer

import hashlib
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from src.infrastructure.config.settings import get_settings
from src.api.models import IngestUploadResponse
from src.application.container import get_ingest_pdfs_use_case

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
    
    use_case = get_ingest_pdfs_use_case()
    
    try:
        result = await use_case.execute(file_bytes=raw, filename=name)
        return {
            "status": result["status"],
            "content_hash": result["content_hash"],
            "doc_id": result["doc_id"],
            "points_upserted": 0,
            "message": result["message"]
        }
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/status/{doc_id}")
async def get_task_status(doc_id: str):
    postgres = PostgresRepository()
    doc = await postgres.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": doc_id, "status": doc.status}
