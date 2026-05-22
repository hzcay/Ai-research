from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
import hashlib
from pathlib import Path

from src.api.models import IngestUploadResponse
from src.application.container import get_document_indexer, get_task_tracker
from src.infrastructure.config.settings import get_settings

router = APIRouter()

def _process_document(raw: bytes, filename: str, content_hash: str, doc_id: str):
    tracker = get_task_tracker()
    settings = get_settings()
    indexer = get_document_indexer()
    try:
        tracker.update_task(doc_id, "processing", 10, "Lưu file tạm thời...")
        upload_root = Path(settings.upload_dir)
        upload_root.mkdir(parents=True, exist_ok=True)
        import re
        base = Path(filename).name
        safe = re.sub(r"[^\w.\-]", "_", base).strip("._") or "upload"
        safe = safe[:200]
        saved = upload_root / f"{content_hash[:16]}_{safe}"
        saved.write_bytes(raw)
        
        tracker.update_task(doc_id, "processing", 30, "Đang phân tích cấu trúc PDF (Docling)...")
        from src.infrastructure.parsing.docling_parser import parse_research_paper
        parsed = parse_research_paper(saved)
        
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
        chunks, _ = indexer._indexer.index_documents([doc])
        n = indexer._indexer.upsert_chunks(chunks)
        
        tracker.update_task(doc_id, "completed", 100, f"Hoàn tất. Đã lưu {n} chunks.")
    except Exception as e:
        tracker.update_task(doc_id, "failed", 0, f"Lỗi: {str(e)}")


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
    
    background_tasks.add_task(_process_document, raw, name, content_hash, doc_id)
    
    return {
        "status": "processing",
        "content_hash": content_hash,
        "doc_id": doc_id,
        "points_upserted": 0,
        "message": "Document is being processed in the background."
    }

@router.get("/status/{doc_id}")
def get_task_status(doc_id: str):
    tracker = get_task_tracker()
    task = tracker.get_task(doc_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
