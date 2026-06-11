from __future__ import annotations

import threading
from typing import Any, Dict

from FlagEmbedding import BGEM3FlagModel

from src.application.ports.embedder_port import EmbedderPort

class BgeEmbedder(EmbedderPort):
    def __init__(self, model_name: str) -> None:
        self._lock = threading.Lock()
        with self._lock:
            self._model = BGEM3FlagModel(model_name, use_fp16=True)

    def encode_query(self, text: str) -> Dict[str, Any]:
        with self._lock:
            output = self._model.encode(
                [text],
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )
        
        dense_vec = output['dense_vecs'][0].tolist()
        lexical_dict = output['lexical_weights'][0]
        
        indices = []
        values = []
        for k, v in lexical_dict.items():
            indices.append(int(k))
            values.append(float(v))
            
        return {
            "dense": dense_vec,
            "sparse": {
                "indices": indices,
                "values": values
            }
        }

    def encode_documents(self, texts: list[str]) -> list[Dict[str, Any]]:
        if not texts:
            return []
        
        with self._lock:
            output = self._model.encode(
                texts,
                batch_size=16,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False
            )
            
        dense_vecs = [v.tolist() for v in output['dense_vecs']]
        lexical_weights = output['lexical_weights']
        
        result = []
        for dense, lex in zip(dense_vecs, lexical_weights):
            indices = []
            values = []
            for k, v in lex.items():
                indices.append(int(k))
                values.append(float(v))
            result.append({
                "dense": dense,
                "sparse": {
                    "indices": indices,
                    "values": values
                }
            })
            
        return result
