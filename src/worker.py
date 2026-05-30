import asyncio
import os
import uuid
import hashlib
import tempfile
from pathlib import Path
from loguru import logger
from arq import Worker
from arq.connections import RedisSettings

from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.infrastructure.storage.minio_storage import MinioStorage
from src.infrastructure.indexing.qdrant_indexer import QdrantIndexer
from src.infrastructure.parsing.docling_parser import parse_research_paper
from src.infrastructure.database.models import Chunk
from src.utils.logger import setup_logging

async def startup(ctx):
    setup_logging()
    logger.info("Starting Worker...")
    settings = get_settings()
    ctx['postgres'] = PostgresRepository()
    ctx['minio'] = MinioStorage()
    ctx['qdrant'] = QdrantIndexer(
        qdrant_url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        embed_model_name=settings.embed_model_name,
    )
    ctx['settings'] = settings

async def process_document(ctx, job_id: str):
    logger.info(f"Processing Job: {job_id}")
    postgres: PostgresRepository = ctx['postgres']
    minio: MinioStorage = ctx['minio']
    qdrant: QdrantIndexer = ctx['qdrant']
    
    # 1. Fetch Job and Document from DB
    job = await postgres.get_ingestion_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found in DB.")
        return
        
    doc = await postgres.get_document(job.doc_id)
    if not doc:
        logger.error(f"Document {job.doc_id} not found in DB.")
        job.status = 'failed'
        await postgres.update_ingestion_job(job)
        return
        
    # Update Status to Processing
    job.status = 'processing'
    doc.status = 'processing'
    await postgres.update_ingestion_job(job)
    await postgres.update_document(doc)
    
    content_hash = hashlib.sha256(f"{doc.id}_{doc.filename}".encode()).hexdigest()
    
    try:
        # Idempotency check: Does it already exist in Qdrant?
        existing = await asyncio.to_thread(qdrant.find_doc_id_by_content_hash, content_hash)
        if existing:
            logger.info(f"Document {doc.id} already indexed. Skipping.")
            job.status = 'completed'
            doc.status = 'completed'
            await postgres.update_ingestion_job(job)
            await postgres.update_document(doc)
            return

        # 2. Download from MinIO
        minio_object_name = doc.minio_path.replace(f"s3://{ctx['settings'].minio_bucket}/", "")
        file_bytes = await asyncio.to_thread(minio.get_object, minio_object_name)
        
        # 3. Parse Document
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            temp_path = Path(tmp.name)
            
        parsed = await asyncio.to_thread(parse_research_paper, temp_path)
        os.unlink(temp_path)
        
        meta = dict(parsed.get("metadata") or {})
        meta["content_hash"] = content_hash
        meta["upload_filename"] = doc.filename

        parsed_doc = {
            "filename": doc.filename,
            "content": str(parsed.get("content") or ""),
            "metadata": meta,
            "content_hash": content_hash,
            "doc_id": doc.id,
        }
        
        # 4. Chunking
        chunks, _ = await asyncio.to_thread(qdrant.index_documents, [parsed_doc])
        
        # 5. Insert Chunks to Postgres
        db_chunks = []
        for i, c in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            c["chunk_id"] = chunk_id
            db_chunks.append(Chunk(
                chunk_id=chunk_id,
                doc_id=doc.id,
                text_content=str(c.get("text", "")),
                chunk_index=i,
                page_start=c.get("metadata", {}).get("page_start", None),
                page_end=c.get("metadata", {}).get("page_end", None),
                token_count=c.get("token_estimate", 0),
                content_hash=content_hash,
                embedding_status="completed"
            ))
        await postgres.create_chunks(db_chunks)
        
        # 6. Upsert Vectors to Qdrant
        await asyncio.to_thread(qdrant.upsert_chunks, chunks)
        
        # 7. Completed
        job.status = 'completed'
        doc.status = 'completed'
        await postgres.update_ingestion_job(job)
        await postgres.update_document(doc)
        logger.info(f"Successfully processed Job {job_id} for Doc {doc.id}")
        
    except Exception as e:
        logger.error(f"Failed to process job {job_id}: {str(e)}")
        job.status = 'failed'
        doc.status = 'failed'
        await postgres.update_ingestion_job(job)
        await postgres.update_document(doc)
        raise e # Let Arq catch it to trigger retry

class WorkerSettings:
    functions = [process_document]
    on_startup = startup
    redis_settings = RedisSettings(host='localhost', port=6379, database=0)
    max_tries = 3
    job_timeout = 3600
