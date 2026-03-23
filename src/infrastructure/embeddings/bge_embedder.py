from __future__ import annotations

from typing import List

from sentence_transformers import SentenceTransformer

from src.application.ports.embedder_port import EmbedderPort


class BgeEmbedder(EmbedderPort):
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def encode_query(self, text: str) -> List[float]:
        vector = self._model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vector.tolist()
