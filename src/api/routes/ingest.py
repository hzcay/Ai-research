from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.models import IngestUploadResponse
from src.application.container import get_document_indexer

router = APIRouter()


@router.post("/upload", response_model=IngestUploadResponse)
async def ingest_upload(
    file: UploadFile = File(...),
    force: str = Form("false"),
) -> IngestUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF file.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    name = file.filename or "upload.pdf"
    force_reindex = force.lower() in ("true", "1", "yes", "on")
    out = get_document_indexer().ingest_pdf_bytes(raw, name, force=force_reindex)
    if not out.get("doc_id") or not out.get("content_hash"):
        raise HTTPException(
            status_code=500,
            detail="Indexing finished without a document id. Check Qdrant and logs.",
        )
    return IngestUploadResponse(**out)
