from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import qdrant_client
from dotenv import load_dotenv
from qdrant_client import models
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

load_dotenv()

client = qdrant_client.QdrantClient(url=os.getenv("QDRANT_URL"))
_embed_model: SentenceTransformer | None = None
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-m3")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "research_chunks")
QDRANT_URL = os.getenv("QDRANT_URL", "")

def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


def _is_qdrant_available() -> tuple[bool, str]:
    """Check Qdrant connectivity and return (ok, message)."""
    try:
        client.get_collections()
        return True, ""
    except Exception as e:
        return False, str(e)

def _strip_frontmatter(markdown_text: str) -> str:
    """Remove YAML frontmatter from markdown if present."""
    if not markdown_text.startswith("---"):
        return markdown_text
    m = re.match(r"^---\n.*?\n---\n", markdown_text, flags=re.DOTALL)
    if m:
        return markdown_text[m.end() :]
    return markdown_text

def _paragraphs_from_markdown(markdown_text: str) -> List[str]:
    """Split markdown body into paragraph-level units."""
    body = _strip_frontmatter(markdown_text)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if not body:
        return []
    parts = [p.strip() for p in body.split("\n\n") if p.strip()]
    return parts

def _is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")

def _extract_blocks_with_tables(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Split markdown into ordered blocks:
      - paragraph block
      - table block (contiguous markdown table lines)
    """
    body = _strip_frontmatter(markdown_text)
    lines = body.splitlines()
    blocks: List[Dict[str, Any]] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        # markdown table block: header + separator + rows
        if _is_table_line(line):
            tbl_lines = [line.strip()]
            i += 1
            while i < len(lines) and _is_table_line(lines[i]):
                tbl_lines.append(lines[i].strip())
                i += 1
            blocks.append({"kind": "table", "text": "\n".join(tbl_lines)})
            continue

        # paragraph block until blank line or table start
        para_lines = [line.rstrip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not _is_table_line(lines[i]):
            para_lines.append(lines[i].rstrip())
            i += 1
        blocks.append({"kind": "paragraph", "text": "\n".join(para_lines).strip()})

    # add running index for linking
    for idx, b in enumerate(blocks, start=1):
        b["block_idx"] = idx
    return blocks

def _estimate_tokens(text: str) -> int:
    """
    Fast token estimate without external tokenizer.
    Roughly matches GPT/BPE scales for English technical text.
    """
    words = len(re.findall(r"\S+", text))
    return max(1, int(words * 1.3))


def _split_oversized_paragraph(paragraph: str, max_tokens: int) -> List[str]:
    """Split one large paragraph into sentence blocks that fit max_tokens."""
    if _estimate_tokens(paragraph) <= max_tokens:
        return [paragraph]

    # sentence-ish split, keep delimiters
    sentences = re.split(r"(?<=[\.\!\?])\s+", paragraph)
    out: List[str] = []
    current: List[str] = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        candidate = " ".join(current + [sent]).strip()
        if current and _estimate_tokens(candidate) > max_tokens:
            out.append(" ".join(current).strip())
            current = [sent]
        else:
            current.append(sent)
    if current:
        out.append(" ".join(current).strip())
    return out


def _build_chunk_id(doc_id: str, idx: int) -> str:
    """Deterministic chunk id for traceability."""
    return f"{doc_id}:chunk:{idx:04d}"


def _build_table_id(doc_id: str, idx: int) -> str:
    return f"{doc_id}:table:{idx:04d}"


def chunk_markdown_by_paragraphs(
    markdown_text: str,
    doc_id: str,
    min_tokens: int = 300,
    max_tokens: int = 800,
) -> List[Dict[str, Any]]:
    """
    Chunk markdown content by paragraph with target token window.
    - Primary unit: paragraph
    - Greedy packing: 300-800 tokens
    - Oversized paragraph: split into sentence blocks
    """
    if min_tokens <= 0 or max_tokens < min_tokens:
        raise ValueError("Invalid token range.")

    paragraphs = _paragraphs_from_markdown(markdown_text)
    prepared: List[str] = []
    for p in paragraphs:
        prepared.extend(_split_oversized_paragraph(p, max_tokens=max_tokens))

    chunks: List[Dict[str, Any]] = []
    buf: List[str] = []
    for p in prepared:
        candidate = "\n\n".join(buf + [p]).strip()
        if buf and _estimate_tokens(candidate) > max_tokens:
            text = "\n\n".join(buf).strip()
            chunks.append(
                {
                    "chunk_id": _build_chunk_id(doc_id, len(chunks) + 1),
                    "text": text,
                    "token_estimate": _estimate_tokens(text),
                }
            )
            buf = [p]
        else:
            buf.append(p)

    if buf:
        text = "\n\n".join(buf).strip()
        chunks.append(
            {
                "chunk_id": _build_chunk_id(doc_id, len(chunks) + 1),
                "text": text,
                "token_estimate": _estimate_tokens(text),
            }
        )

    return chunks

def chunk_markdown_with_tables(
    markdown_text: str,
    doc_id: str,
    min_tokens: int = 300,
    max_tokens: int = 800,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Build two stores:
      - content chunks (paragraph-packed, 300-800 tokens)
      - table chunks (one markdown table per chunk)
    Linked by:
      - content_chunk.related_table_ids
      - table_chunk.related_chunk_ids
    """
    if min_tokens <= 0 or max_tokens < min_tokens:
        raise ValueError("Invalid token range.")

    blocks = _extract_blocks_with_tables(markdown_text)
    paragraph_units: List[Dict[str, Any]] = []
    table_chunks: List[Dict[str, Any]] = []

    for b in blocks:
        if b["kind"] == "table":
            text = b["text"].strip()
            table_chunks.append(
                {
                    "table_id": _build_table_id(doc_id, len(table_chunks) + 1),
                    "chunk_type": "table",
                    "text": text,
                    "token_estimate": _estimate_tokens(text),
                    "block_idx": b["block_idx"],
                    "related_chunk_ids": [],
                }
            )
        else:
            for part in _split_oversized_paragraph(b["text"], max_tokens=max_tokens):
                paragraph_units.append({"text": part, "block_idx": b["block_idx"]})

    content_chunks: List[Dict[str, Any]] = []
    buf_texts: List[str] = []
    buf_blocks: List[int] = []
    for p in paragraph_units:
        candidate = "\n\n".join(buf_texts + [p["text"]]).strip()
        if buf_texts and _estimate_tokens(candidate) > max_tokens:
            text = "\n\n".join(buf_texts).strip()
            content_chunks.append(
                {
                    "chunk_id": _build_chunk_id(doc_id, len(content_chunks) + 1),
                    "chunk_type": "content",
                    "text": text,
                    "token_estimate": _estimate_tokens(text),
                    "related_table_ids": [],
                    "_block_indices": sorted(set(buf_blocks)),
                }
            )
            buf_texts = [p["text"]]
            buf_blocks = [p["block_idx"]]
        else:
            buf_texts.append(p["text"])
            buf_blocks.append(p["block_idx"])

    if buf_texts:
        text = "\n\n".join(buf_texts).strip()
        content_chunks.append(
            {
                "chunk_id": _build_chunk_id(doc_id, len(content_chunks) + 1),
                "chunk_type": "content",
                "text": text,
                "token_estimate": _estimate_tokens(text),
                "related_table_ids": [],
                "_block_indices": sorted(set(buf_blocks)),
            }
        )

    for t in table_chunks:
        if not content_chunks:
            break
        nearest = min(
            content_chunks,
            key=lambda c: min(abs(t["block_idx"] - bi) for bi in c["_block_indices"]),
        )
        nearest["related_table_ids"].append(t["table_id"])
        t["related_chunk_ids"].append(nearest["chunk_id"])

    for c in content_chunks:
        c.pop("_block_indices", None)
    for t in table_chunks:
        t.pop("block_idx", None)

    return content_chunks, table_chunks

def test_chunk_sizes(
    chunks: List[Dict[str, Any]],
    min_tokens: int = 300,
    max_tokens: int = 800,
) -> Dict[str, Any]:
    """Validate chunk sizes and return diagnostics report."""
    sizes = [int(c.get("token_estimate", 0)) for c in chunks]
    if not sizes:
        return {
            "total_chunks": 0,
            "within_range": 0,
            "below_min": 0,
            "above_max": 0,
            "min_size": 0,
            "max_size": 0,
            "avg_size": 0.0,
        }
    within = sum(1 for s in sizes if min_tokens <= s <= max_tokens)
    below = sum(1 for s in sizes if s < min_tokens)
    above = sum(1 for s in sizes if s > max_tokens)
    return {
        "total_chunks": len(sizes),
        "within_range": within,
        "below_min": below,
        "above_max": above,
        "min_size": min(sizes),
        "max_size": max(sizes),
        "avg_size": round(sum(sizes) / len(sizes), 2),
    }


def create_collection(collection_name: str, vector_size: int) -> None:
    """Create Qdrant collection if missing."""
    existing = {c.name for c in client.get_collections().collections}
    if collection_name in existing:
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def _embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate dense embeddings with BAAI/bge-m3 via sentence-transformers."""
    if not texts:
        return []
    model = _get_embed_model()
    vecs = model.encode(
        texts,
        batch_size=16,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return [v.tolist() for v in vecs]


def upsert_chunks_to_qdrant(
    chunks: List[Dict[str, Any]],
    collection_name: str = QDRANT_COLLECTION,
) -> int:
    """
    Upsert chunk vectors into Qdrant.
    Each point id uses stable hash of chunk_id/table_id.
    """
    if not chunks:
        return 0

    ok, err = _is_qdrant_available()
    if not ok:
        print(f"[WARN] Qdrant unavailable at `{QDRANT_URL}`: {err}")
        print("[WARN] Skipping upsert. Start Qdrant then rerun indexing.")
        return 0

    texts = [str(c.get("text", "")) for c in chunks]
    vectors = _embed_texts(texts)
    if not vectors:
        return 0

    vector_size = len(vectors[0])
    create_collection(collection_name=collection_name, vector_size=vector_size)

    points: List[models.PointStruct] = []
    for c, vec in zip(chunks, vectors):
        external_id = str(c.get("chunk_id") or c.get("table_id"))
        point_id = int(hashlib.sha1(external_id.encode("utf-8")).hexdigest()[:16], 16)
        payload = {
            "external_id": external_id,
            "doc_id": c.get("doc_id"),
            "filename": c.get("filename"),
            "chunk_type": c.get("chunk_type"),
            "token_estimate": c.get("token_estimate"),
            "text": c.get("text"),
            "related_table_ids": c.get("related_table_ids", []),
            "related_chunk_ids": c.get("related_chunk_ids", []),
            "metadata": c.get("metadata", {}),
        }
        points.append(models.PointStruct(id=point_id, vector=vec, payload=payload))

    client.upsert(collection_name=collection_name, points=points, wait=True)
    return len(points)


def index_documents(
    docs: List[Dict[str, Any]],
    *,
    min_tokens: int = 300,
    max_tokens: int = 800,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Build paragraph chunks with chunk_id and run size tests.
    Expects each doc has at least: filename (optional), content (markdown).

    Returns:
      - all chunks
      - per-doc test reports
    """
    all_chunks: List[Dict[str, Any]] = []
    reports: List[Dict[str, Any]] = []

    for i, doc in enumerate(docs, start=1):
        filename = str(doc.get("filename", f"doc_{i}"))
        doc_id = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]
        content = str(doc.get("content", ""))
        meta = dict(doc.get("metadata", {}))

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

        for t in table_chunks:
            t["doc_id"] = doc_id
            t["filename"] = filename
            t["metadata"] = meta

        report = test_chunk_sizes(content_chunks, min_tokens=min_tokens, max_tokens=max_tokens)
        report["doc_id"] = doc_id
        report["filename"] = filename
        report["content_chunks"] = len(content_chunks)
        report["table_chunks"] = len(table_chunks)
        reports.append(report)
        all_chunks.extend(content_chunks)
        all_chunks.extend(table_chunks)

    return all_chunks, reports


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    processed_dir = repo_root / "data" / "processed"
    md_files = sorted(processed_dir.glob("*.md"))
    if not md_files:
        print("No processed markdown files found.")
    else:
        docs: List[Dict[str, Any]] = []
        for fp in md_files:
            docs.append({"filename": fp.name, "content": fp.read_text(encoding="utf-8"), "metadata": {}})

        chunks, reports = index_documents(docs, min_tokens=300, max_tokens=800)
        print(f"Docs   : {len(docs)}")
        print(f"Chunks : {len(chunks)}")
        print("Chunk size report (300-800 tokens):")
        for r in reports:
            print(
                f"- {r['filename']}: content={r['content_chunks']}, tables={r['table_chunks']}, "
                f"total={r['total_chunks']}, within={r['within_range']}, "
                f"below={r['below_min']}, above={r['above_max']}, "
                f"min={r['min_size']}, max={r['max_size']}, avg={r['avg_size']}"
            )

        inserted = upsert_chunks_to_qdrant(chunks, collection_name=QDRANT_COLLECTION)
        print(f"Upsert : {inserted} points -> collection `{QDRANT_COLLECTION}`")
        print(f"Model  : {EMBED_MODEL_NAME}")
        print(f"Qdrant : {QDRANT_URL}")