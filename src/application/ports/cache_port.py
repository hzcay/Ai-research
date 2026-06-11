from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class SemanticCachePort(ABC):
    @abstractmethod
    async def get(
        self,
        query: str,
        query_vector: list[float],
        tenant_id: str,
        threshold: float = 0.92
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def set(
        self,
        query: str,
        query_vector: list[float],
        answer: str,
        sources: list[dict],
        tenant_id: str,
        metadata: dict
    ) -> None:
        pass


class ChunkCachePort(ABC):
    @abstractmethod
    def get_chunk_text(self, chunk_id: str) -> Optional[str]:
        pass

    @abstractmethod
    def set_chunk_text(self, chunk_id: str, text: str) -> None:
        pass

    @abstractmethod
    def get_multiple_chunks(self, chunk_ids: list[str]) -> Dict[str, str]:
        pass