from typing import List

class RerankerPort:
    def rerank(self, query: str, texts: List[str]) -> List[float]:
        raise NotImplementedError
