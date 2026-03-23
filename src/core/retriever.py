from __future__ import annotations

from typing import Any, Dict, List
from dotenv import load_dotenv
load_dotenv()

try:
    from indexer import (
        QDRANT_COLLECTION,
        _get_embed_model,
        _is_qdrant_available,
        client,
    )
except ImportError:
    from src.core.indexer import (
        QDRANT_COLLECTION,
        _get_embed_model,
        _is_qdrant_available,
        client,
    )


def _query_collection(
    collection_name: str,
    query_vector: List[float],
    top_k: int,
) -> List[Any]:
    """
    Run nearest-neighbor search. New qdrant-client uses query_points(list[float]=vector);
    older versions expose search(query_vector=...).
    """
    if hasattr(client, "query_points"):
        resp = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return list(resp.points)

    if hasattr(client, "search"):
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )

    raise AttributeError(
        "QdrantClient has neither query_points nor search; upgrade qdrant-client."
    )

def retrieve(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Embed the query with the same model as indexing (BAAI/bge-m3 by default),
    then vector-search Qdrant.
    """
    ok, err = _is_qdrant_available()
    if not ok:
        raise ConnectionError(f"Qdrant unavailable: {err}")

    model = _get_embed_model()
    vec = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    query_vector = vec.tolist()

    hits = _query_collection(QDRANT_COLLECTION, query_vector, top_k)
    out: List[Dict[str, Any]] = []
    for p in hits:
        out.append(
            {
                "id": p.id,
                "score": getattr(p, "score", None),
                "payload": p.payload if getattr(p, "payload", None) is not None else {},
            }
        )
    return out


if __name__ == "__main__":
    results = retrieve("what is hunyuan3d?")
    print(results)