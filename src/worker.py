import asyncio
import os
import uuid
import hashlib
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import json
from loguru import logger
from arq import Worker
from arq.connections import RedisSettings

from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.postgres_repository import PostgresRepository
from src.infrastructure.storage.minio_storage import MinioStorage
from src.infrastructure.indexing.qdrant_indexer import QdrantIndexer
from src.infrastructure.parsing.docling_parser import parse_research_paper
from src.infrastructure.database.models import Chunk
from src.utils.logger import setup_logger

from src.application.container import get_process_document_use_case

load_dotenv()

async def startup(ctx):
    setup_logger()
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
    logger.info(f"Processing Job/Doc ID: {job_id}")
    
    use_case = get_process_document_use_case()
    
    try:
        await use_case.execute(job_id)
        logger.info(f"Successfully processed Doc {job_id}")
    except Exception as e:
        logger.error(f"Failed to process Doc {job_id}: {str(e)}")
        raise e

class WorkerSettings:
    functions = [process_document]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    max_tries = 3
    job_timeout = 3600
