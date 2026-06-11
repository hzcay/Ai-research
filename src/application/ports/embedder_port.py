from __future__ import annotations

from typing import Any, Dict, Protocol


class EmbedderPort(Protocol):
    def encode_query(self, text: str) -> Dict[str, Any]:
        ...
        
    def encode_documents(self, texts: list[str]) -> list[Dict[str, Any]]:
        ...

