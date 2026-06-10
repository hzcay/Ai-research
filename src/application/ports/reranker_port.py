from typing import List

class RerankerPort:
    def rerank(self, query: str, texts: List[str]) -> List[float]:
        """
        Reranks a list of texts based on their relevance to a query.
        Returns a list of relevance scores (floats) corresponding to each text.
        """
        raise NotImplementedError
