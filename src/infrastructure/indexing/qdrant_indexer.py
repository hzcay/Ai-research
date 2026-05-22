from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Tuple

import qdrant_client
from qdrant_client import models
from qdrant_client.http.models import Distance, VectorParams, SparseVectorParams, SparseIndexParams
from FlagEmbedding import BGEM3FlagModel

from src.infrastructure.indexing.chunker import (
    build_doc_id,
    chunk_markdown_with_tables,
    test_chunk_sizes,
)

_EMBED_MODELS: dict[str, BGEM3FlagModel] = {}


def _get_embed_model(model_name: str) -> BGEM3FlagModel:
    model = _EMBED_MODELS.get(model_name)
    if model is None:
        model = BGEM3FlagModel(model_name, use_fp16=True)
        _EMBED_MODELS[model_name] = model
    return model


class QdrantIndexer:
    def __init__(self, qdrant_url: str, collection_name: str, embed_model_name: str) -> None:
        self._client = qdrant_client.QdrantClient(url=qdrant_url)
        self._qdrant_url = qdrant_url
        self._collection_name = collection_name
        self._embed_model_name = embed_model_name

    def index_documents(
        self,
        docs: List[Dict[str, Any]],
        *,
        min_tokens: int = 300,
        max_tokens: int = 800,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        all_chunks: List[Dict[str, Any]] = []
        reports: List[Dict[str, Any]] = []

        for i, doc in enumerate(docs, start=1):
            filename = str(doc.get("filename", f"doc_{i}"))
            doc_id = str(doc.get("doc_id") or build_doc_id(filename))
            content = str(doc.get("content", ""))
            meta = dict(doc.get("metadata", {}))
            content_hash = doc.get("content_hash")
            if content_hash:
                meta["content_hash"] = content_hash

            content_chunks, table_chunks = chunk_markdown_with_tables(
                content,
                doc_id=doc_id,
                min_tokens=min_tokens,
                max_tokens=max_tokens,
            )
            for c in content_chunks:
                c["doc_id"] = doc_id
                c["filename"] = filename
                c["metadata"] = meta
                if content_hash:
                    c["content_hash"] = content_hash
            for t in table_chunks:
                t["doc_id"] = doc_id
                t["filename"] = filename
                t["metadata"] = meta
                if content_hash:
                    t["content_hash"] = content_hash

            report = test_chunk_sizes(content_chunks, min_tokens=min_tokens, max_tokens=max_tokens)
            report["doc_id"] = doc_id
            report["filename"] = filename
            report["content_chunks"] = len(content_chunks)
            report["table_chunks"] = len(table_chunks)
            reports.append(report)
            all_chunks.extend(content_chunks)
            all_chunks.extend(table_chunks)

        return all_chunks, reports

    def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0

        ok, err = self._is_qdrant_available()
        if not ok:
            print(f"[WARN] Qdrant unavailable at `{self._qdrant_url}`: {err}")
            print("[WARN] Skipping upsert. Start Qdrant then rerun indexing.")
            return 0

        texts = [str(c.get("text", "")) for c in chunks]
        vectors = self._embed_texts(texts)
        if not vectors:
            return 0

        self._create_collection(vector_size=len(vectors[0]["dense"]))

        points: List[models.PointStruct] = []
        for c, vec in zip(chunks, vectors):
            external_id = str(c.get("chunk_id") or c.get("table_id"))
            point_id = int(hashlib.sha1(external_id.encode("utf-8")).hexdigest()[:16], 16)
            payload = {
                "external_id": external_id,
                "doc_id": c.get("doc_id"),
                "content_hash": c.get("content_hash"),
                "filename": c.get("filename"),
                "chunk_type": c.get("chunk_type"),
                "token_estimate": c.get("token_estimate"),
                "text": c.get("text"),
                "related_table_ids": c.get("related_table_ids", []),
                "related_chunk_ids": c.get("related_chunk_ids", []),
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

    def _embed_texts(self, texts: List[str]) -> List[Dict[str, Any]]:
        if not texts:
            return []
        model = _get_embed_model(self._embed_model_name)
        output = model.encode(
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

    def find_doc_id_by_content_hash(self, content_hash: str) -> str | None:
        if not content_hash:
            return None
        ok, _ = self._is_qdrant_available()
        if not ok:
            return None
        flt = models.Filter(
            must=[
                models.FieldCondition(
                    key="content_hash",
                    match=models.MatchValue(value=content_hash),
                )
            ]
        )
        try:
            points, _ = self._client.scroll(
                collection_name=self._collection_name,
                scroll_filter=flt,
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
            if not points:
                return None
            p0 = points[0]
            payload = getattr(p0, "payload", None) or {}
            doc_id = payload.get("doc_id")
            return str(doc_id) if doc_id else None
        except Exception as e:
            if "Not found: Collection" in str(e):
                return None
            raise
