from typing import List
from src.application.ports.reranker_port import RerankerPort

class NoOpReranker(RerankerPort):
    def rerank(self, query: str, texts: List[str]) -> List[float]:
        return [1.0] * len(texts) if texts else []
