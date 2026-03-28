from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    auto_expand_corpus: bool = True


class ChatResponse(BaseModel):
    answer: str
    contexts: List[Dict[str, Any]]
    retrieval_scope: Optional[str] = None


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