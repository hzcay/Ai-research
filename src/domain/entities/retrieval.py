from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(slots=True)
class RetrievedChunk:
    id: str # chunk_id
    doc_id: str
    score: float | None
    text: str
    page_start: int | None = None
    page_end: int | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
