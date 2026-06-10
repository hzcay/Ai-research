import threading
from typing import List, Optional, Any
from loguru import logger
from src.application.ports.reranker_port import RerankerPort

class BgeReranker(RerankerPort):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self._model_name = model_name
        self._lock = threading.Lock()
        self._model: Optional[Any] = None

    def _lazy_load_model(self):
        if self._model is None:
            logger.info(f"Lazy loading BgeReranker model: {self._model_name}...")
            from FlagEmbedding import FlagReranker
            self._model = FlagReranker(self._model_name, use_fp16=True)
            logger.info(f"BgeReranker model loaded successfully.")

    def rerank(self, query: str, texts: List[str]) -> List[float]:
        if not texts:
            return []
        
        with self._lock:
            self._lazy_load_model()
            
            pairs = [[query, text] for text in texts]
            scores = self._model.compute_score(pairs)
            
            if isinstance(scores, float):
                return [scores]
            return scores
