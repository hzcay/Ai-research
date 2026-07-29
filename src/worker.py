import os
from dotenv import load_dotenv
from loguru import logger
from arq import cron
from arq.connections import RedisSettings

from src.infrastructure.config.settings import get_settings
from src.utils.logger import setup_logger
from src.application.container import (
    get_process_document_use_case,
    get_postgres_repository,
    get_task_queue_adapter,
)

load_dotenv()

async def startup(ctx):
    setup_logger()
    logger.info("Starting Worker...")
    ctx["postgres"] = get_postgres_repository()

async def process_document(ctx, job_id: str):
    logger.info(f"Processing Job/Doc ID: {job_id}")
    
    use_case = get_process_document_use_case()
    
    repository = get_postgres_repository()
    ingestion_job = await repository.get_ingestion_job_by_doc_id(job_id)
    if ingestion_job:
        ingestion_job.status = "processing"
        ingestion_job.error_message = None
        await repository.update_ingestion_job(ingestion_job)
    try:
        await use_case.execute(job_id)
        if ingestion_job:
            ingestion_job.status = "completed"
            ingestion_job.error_message = None
            await repository.update_ingestion_job(ingestion_job)
        logger.info(f"Successfully processed Doc {job_id}")
    except Exception as e:
        logger.error(f"Failed to process Doc {job_id}: {str(e)}")
        job_try = int(ctx.get("job_try", 1))
        max_tries = WorkerSettings.max_tries
        if ingestion_job:
            ingestion_job.status = "failed" if job_try >= max_tries else "retrying"
            ingestion_job.error_message = str(e)[:1000]
            await repository.update_ingestion_job(ingestion_job)
        if job_try < max_tries:
            document = await repository.get_document(job_id)
            if document:
                document.status = "retrying"
                await repository.update_document(document)
        raise


async def reconcile_ingestion_jobs(ctx):
    """Re-enqueue durable jobs that were saved while Redis was unavailable."""
    repository = get_postgres_repository()
    queue = get_task_queue_adapter()
    jobs = await repository.list_ingestion_jobs_by_status(
        ["pending_enqueue", "enqueue_failed"]
    )
    for job in jobs:
        try:
            queue_job_id = job.queue_job_id or f"ingest:{job.doc_id}:{job.id}"
            enqueued = await queue.enqueue_job(
                "process_document", job.doc_id, _job_id=queue_job_id
            )
            job.status = "queued"
            job.error_message = None
            job.queue_job_id = queue_job_id
            await repository.update_ingestion_job(job)
        except Exception as exc:
            job.status = "enqueue_failed"
            job.error_message = str(exc)[:1000]
            await repository.update_ingestion_job(job)

class WorkerSettings:
    functions = [process_document]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    max_tries = 3
    job_timeout = 3600
    cron_jobs = [cron(reconcile_ingestion_jobs, minute=set(range(60)))]
