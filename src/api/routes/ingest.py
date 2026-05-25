from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
import hashlib
from pathlib import Path
import threading
import time
import sys
from loguru import logger

from src.api.models import IngestUploadResponse
from src.application.container import get_document_indexer, get_task_tracker
from src.infrastructure.config.settings import get_settings

router = APIRouter()

INGESTION_SEMAPHORE = threading.Semaphore(2)

def _get_peak_memory_mb() -> float:
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return usage / (1024 * 1024)
        return usage / 1024
    except ImportError:
        return 0.0

def _process_document(saved_path: Path, filename: str, content_hash: str, doc_id: str):
    tracker = get_task_tracker()
    settings = get_settings()
    indexer = get_document_indexer()
    
    tracker.update_task(doc_id, "processing", 5, "Đang chờ đến lượt xử lý (Queue)...")
    logger.info(f"Task {doc_id} waiting for execution slot...")
    
    with INGESTION_SEMAPHORE:
        logger.info(f"Task {doc_id} acquired slot. Starting ingestion.")
        start_time = time.time()
        parsing_time = 0.0
        embedding_time = 0.0
        upsert_time = 0.0
        
        try:
            tracker.update_task(doc_id, "processing", 10, "Bắt đầu xử lý file tạm...")
            saved = saved_path
            
            tracker.update_task(doc_id, "processing", 30, "Đang phân tích cấu trúc PDF (Docling)...")
            t0 = time.time()
            from src.infrastructure.parsing.docling_parser import parse_research_paper
            parsed = parse_research_paper(saved)
            parsing_time = time.time() - t0
            
            meta = dict(parsed.get("metadata") or {})
            meta["content_hash"] = content_hash
            meta["upload_filename"] = filename
            
            doc = {
                "filename": str(parsed.get("filename") or safe),
                "content": str(parsed.get("content") or ""),
                "metadata": meta,
                "content_hash": content_hash,
                "doc_id": doc_id,
            }
            
            tracker.update_task(doc_id, "processing", 70, "Đang cắt và nhúng văn bản (BGE-M3)...")
            t1 = time.time()
            chunks, _ = indexer._indexer.index_documents([doc])
            embedding_time = time.time() - t1

            t2 = time.time()
            n = indexer._indexer.upsert_chunks(chunks)
            upsert_time = time.time() - t2
            
            tracker.update_task(doc_id, "completed", 100, f"Hoàn tất. Đã lưu {n} chunks.")
            
            total_time = time.time() - start_time
            peak_mem = _get_peak_memory_mb()
            
            logger.success(
                f"[METRICS] Ingestion SUCCESS for {doc_id}:\n"
                f" - Total Time: {total_time:.2f}s\n"
                f" - Parsing Time: {parsing_time:.2f}s\n"
                f" - Embedding Time: {embedding_time:.2f}s\n"
                f" - Upsert Time: {upsert_time:.2f}s\n"
                f" - Peak Memory: {peak_mem:.2f} MB\n"
                f" - Success Count: 1"
            )
        except Exception as e:
            tracker.update_task(doc_id, "failed", 0, f"Lỗi: {str(e)}")
            total_time = time.time() - start_time
            logger.error(
                f"[METRICS] Ingestion FAILED for {doc_id}:\n"
                f" - Error: {str(e)}\n"
                f" - Total Time (before fail): {total_time:.2f}s\n"
                f" - Fail Count: 1"
            )


@router.post("/upload", response_model=IngestUploadResponse)
async def ingest_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    force: str = Form("false"),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF file.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    name = file.filename or "upload.pdf"
    force_reindex = force.lower() in ("true", "1", "yes", "on")
    
    content_hash = hashlib.sha256(raw).hexdigest()
    doc_id = hashlib.sha1(content_hash.encode("ascii")).hexdigest()[:12]
    
    indexer = get_document_indexer()
    if not force_reindex:
        existing = indexer._indexer.find_doc_id_by_content_hash(content_hash)
        if existing:
            return {
                "status": "duplicate",
                "content_hash": content_hash,
                "doc_id": existing,
                "points_upserted": 0,
                "message": "Same PDF bytes already indexed."
            }
            
    tracker = get_task_tracker()
    tracker.create_task(doc_id)
    
    # TỐI ƯU RAM: Ghi file xuống ổ cứng ngay lập tức, không để ngậm trên RAM
    settings = get_settings()
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    import re
    safe = re.sub(r"[^\w.\-]", "_", name).strip("._") or "upload"
    saved_path = upload_root / f"{content_hash[:16]}_{safe[:200]}"
    saved_path.write_bytes(raw)
    
    # Chỉ ném "đường dẫn" vào Queue thay vì cả cục bytes
    background_tasks.add_task(_process_document, saved_path, name, content_hash, doc_id)
    
    return {
        "status": "processing",
        "content_hash": content_hash,
        "doc_id": doc_id,
        "points_upserted": 0,
        "message": "Document is being processed in the background."
    }

@router.get("/status/{doc_id}")
async def get_task_status(doc_id: str):
    tracker = get_task_tracker()
    task = tracker.get_task(doc_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
