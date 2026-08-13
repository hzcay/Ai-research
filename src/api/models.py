from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    document_id: Optional[str] = None
    auto_expand_corpus: bool = True
    project_id: Optional[str] = None

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
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=50)
    document_id: Optional[str] = None
    project_id: Optional[str] = None

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


class ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    research_question: str = Field(min_length=5, max_length=5000)


class MemberUpsertRequest(BaseModel):
    user_id: Optional[str] = None
    role: str
    email: Optional[str] = None


class ScopeCreateRequest(BaseModel):
    research_question: str = Field(min_length=5, max_length=5000)
    framework: str = "freeform"
    population: Optional[str] = None
    intervention: Optional[str] = None
    comparison: Optional[str] = None
    outcomes: Optional[str] = None
    study_types: Optional[str] = None
    date_from: Optional[int] = None
    date_to: Optional[int] = None
    languages: List[str] = Field(default_factory=list)
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)
    change_note: Optional[str] = None


class ScopeReviewRequest(BaseModel):
    decision: str
    comment: Optional[str] = Field(default=None, max_length=4000)


class ProjectStatusRequest(BaseModel):
    status: str


class WorkflowStartRequest(BaseModel):
    workflow_type: str = Field(min_length=1, max_length=100)
    input_hash: Optional[str] = None
    idempotency_key: Optional[str] = None
