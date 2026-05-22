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