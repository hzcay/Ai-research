from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from src.api.models import IngestUploadResponse
from src.application.container import get_ingest_pdfs_use_case, get_postgres_repository
from src.infrastructure.config.settings import get_settings

router = APIRouter()

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
    settings = get_settings()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds the upload size limit.")
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="File content is not a valid PDF.")
        
    name = file.filename or "upload.pdf"
    
    use_case = get_ingest_pdfs_use_case()
    
    try:
        force_replace = force.strip().lower() in {"1", "true", "yes", "on"}
        result = await use_case.execute(
            file_bytes=raw, filename=name, force=force_replace
        )
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
    postgres = get_postgres_repository()
    doc = await postgres.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    job = await postgres.get_ingestion_job_by_doc_id(doc_id)
    progress_by_status = {
        "queued": 5,
        "retrying": 25,
        "processing": 40,
        "completed": 100,
        "failed": 100,
    }
    messages = {
        "queued": "Waiting for a worker.",
        "retrying": "A temporary failure occurred; processing will retry.",
        "processing": "Parsing and indexing the document.",
        "completed": "Document is ready.",
        "failed": "Document processing failed.",
    }
    return {
        "doc_id": doc_id,
        "status": doc.status,
        "progress": progress_by_status.get(doc.status, 0),
        "message": messages.get(doc.status, doc.status),
        "job_status": job.status if job else None,
        "error": job.error_message if job and job.status == "failed" else None,
    }
