from __future__ import annotations

from typing import List, Protocol


class EmbedderPort(Protocol):
    def encode_query(self, text: str) -> List[float]:
        ...
