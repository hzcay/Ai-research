from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    auto_expand_corpus: bool = True

class Citation(BaseModel):
    id: int
    document_name: str
    page: Optional[int] = None
    chunk_id: str
    score: float
    text: str

class RetrievalDebug(BaseModel):
    retrieval_mode: str
    cache_hit: bool
    embedding_ms: float
    retrieval_ms: float
    llm_ms: float
    total_ms: float
    top_k: int

class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    debug: RetrievalDebug

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    document_id: Optional[str] = None

class IngestUploadResponse(BaseModel):
    status: str
    content_hash: str
    doc_id: str
    points_upserted: int = 0
    saved_path: Optional[str] = None
    message: Optional[str] = None

class SearchResult(BaseModel):
    id: Optional[str] = None
    score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: List[SearchResult]