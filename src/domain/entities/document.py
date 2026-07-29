from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass(slots=True)
class Document:
    id: str
    filename: str
    minio_path: Optional[str] = None
    markdown_path: Optional[str] = None
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata_: Dict[str, Any] = field(default_factory=dict)
    content_hash: Optional[str] = None

@dataclass(slots=True)
class IngestionJob:
    id: str
    doc_id: str
    status: str = "queued"
    created_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    queue_job_id: Optional[str] = None

@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text_content: str
    chunk_index: int
    parent_id: Optional[str] = None
    chunk_type: str = "child"
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    token_count: Optional[int] = None
    content_hash: Optional[str] = None
    section_path: Optional[str] = None
    source_content_hash: Optional[str] = None
    embedding_status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)
