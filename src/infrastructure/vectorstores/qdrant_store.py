from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

import qdrant_client
from qdrant_client import models

from src.application.ports.vector_store_port import VectorStorePort
from src.application.ports.embedder_port import EmbedderPort
from src.domain.entities.retrieval import RetrievedChunk
import hashlib
from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams, SparseIndexParams


def _doc_id_filter(document_id: Optional[str]) -> Optional[models.Filter]:
    if not document_id:
        return None
    return models.Filter(
        must=[
            models.FieldCondition(
                key="doc_id",
                match=models.MatchValue(value=document_id),
            )
        ]
    )


class QdrantVectorStore(VectorStorePort):
    def __init__(
        self,
        qdrant_url: str,
        collection_name: str,
        embedder: EmbedderPort,
        timeout_s: float = 10.0,
        retries: int = 2,
        lexical_candidate_limit: int = 1000,
    ) -> None:
        self._client = qdrant_client.QdrantClient(url=qdrant_url, timeout=timeout_s)
        self._collection_name = collection_name
        self._embedder = embedder
        self._retries = max(0, retries)

    def search(
        self,
        query_vectors: Dict[str, Any],
        top_k: int,
        document_id: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        hits = self._query(query_vectors=query_vectors, top_k=top_k, document_id=document_id)
        output: List[RetrievedChunk] = []
        for hit in hits:
            payload = getattr(hit, "payload", None) or {}
            
            real_chunk_id = payload.get("external_id") or str(getattr(hit, "id", ""))
            
            output.append(
                RetrievedChunk(
                    id=real_chunk_id,
                    doc_id=payload.get("doc_id", ""),
                    score=getattr(hit, "score", None),
                    text="", 
                    page_start=payload.get("page"),
                    metadata=payload,
                )
            )
        return output

    def _query(
        self,
        query_vectors: Dict[str, Any],
        top_k: int,
        document_id: Optional[str] = None,
    ) -> List[Any]:
        qf = _doc_id_filter(document_id)
        
        dense_vec = query_vectors.get("dense")
        sparse_vec = query_vectors.get("sparse")
        
        prefetch = []
        if dense_vec:
            p = models.Prefetch(
                query=dense_vec,
                using="dense",
                limit=top_k * 3,
            )
            if qf is not None:
                p.filter = qf
            prefetch.append(p)
            
        if sparse_vec:
            p = models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_vec["indices"],
                    values=sparse_vec["values"]
                ),
                using="sparse",
                limit=top_k * 3,
            )
            if qf is not None:
                p.filter = qf
            prefetch.append(p)

        for attempt in range(self._retries + 1):
            try:
                response = self._client.query_points(
                    collection_name=self._collection_name,
                    prefetch=prefetch,
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=top_k,
                    with_payload=True,
                )
                return list(response.points)
            except Exception as e:
                    return []
                if attempt >= self._retries:
                    raise
                time.sleep(0.2 * math.pow(2, attempt))
        return []

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0

        ok, err = self._is_qdrant_available()
        if not ok:
            print(f"[WARN] Qdrant unavailable at `{self._client._url}`: {err}")
            return 0

        texts = [str(c.get("text", "")) for c in chunks]
        
        # We need a batched encode. Since EmbedderPort only has encode_query right now,
        # we will hack it using encode_query in a loop, or better, we should update EmbedderPort.
        # But BGEM3FlagModel can batch encode.
        # Since we injected `BgeEmbedder`, let's assume it has an internal model we can use, 
        # or we just loop for now to make it runnable without breaking EmbedderPort.
        vectors = []
        for text in texts:
            # We use encode_query since it returns dict with dense and sparse
            vec = self._embedder.encode_query(text)
            vectors.append(vec)

        self._create_collection(vector_size=len(vectors[0]["dense"]))

        points: List[models.PointStruct] = []
        for c, vec in zip(chunks, vectors):
            external_id = str(c.get("chunk_id") or c.get("table_id"))
            point_id = int(hashlib.sha1(external_id.encode("utf-8")).hexdigest()[:16], 16)
            payload = {
                "external_id": external_id,
                "parent_id": c.get("parent_id"),
                "doc_id": c.get("doc_id"),
                "content_hash": c.get("content_hash"),
                "filename": c.get("filename"),
                "chunk_type": c.get("chunk_type"),
                "token_estimate": c.get("token_estimate"),
                "metadata": c.get("metadata", {}),
            }
            
            qdrant_vector = {
                "dense": vec["dense"],
                "sparse": models.SparseVector(
                    indices=vec["sparse"]["indices"],
                    values=vec["sparse"]["values"]
                )
            }
            
            points.append(models.PointStruct(id=point_id, vector=qdrant_vector, payload=payload))

        self._client.upsert(collection_name=self._collection_name, points=points, wait=True)
        return len(points)

    def _is_qdrant_available(self) -> tuple[bool, str]:
        try:
            self._client.get_collections()
            return True, ""
        except Exception as e:
            return False, str(e)

    def _create_collection(self, vector_size: int) -> None:
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection_name in existing:
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config={
                "dense": VectorParams(size=vector_size, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(
                        on_disk=False,
                    )
                )
            }
        )

