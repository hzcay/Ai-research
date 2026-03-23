from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Tuple


def _strip_frontmatter(markdown_text: str) -> str:
    if not markdown_text.startswith("---"):
        return markdown_text
    m = re.match(r"^---\n.*?\n---\n", markdown_text, flags=re.DOTALL)
    if m:
        return markdown_text[m.end() :]
    return markdown_text


def _is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|")


def _extract_blocks_with_tables(markdown_text: str) -> List[Dict[str, Any]]:
    body = _strip_frontmatter(markdown_text)
    lines = body.splitlines()
    blocks: List[Dict[str, Any]] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        if _is_table_line(line):
            tbl_lines = [line.strip()]
            i += 1
            while i < len(lines) and _is_table_line(lines[i]):
                tbl_lines.append(lines[i].strip())
                i += 1
            blocks.append({"kind": "table", "text": "\n".join(tbl_lines)})
            continue

        para_lines = [line.rstrip()]
        i += 1
        while i < len(lines) and lines[i].strip() and not _is_table_line(lines[i]):
            para_lines.append(lines[i].rstrip())
            i += 1
        blocks.append({"kind": "paragraph", "text": "\n".join(para_lines).strip()})

    for idx, b in enumerate(blocks, start=1):
        b["block_idx"] = idx
    return blocks


def _estimate_tokens(text: str) -> int:
    words = len(re.findall(r"\S+", text))
    return max(1, int(words * 1.3))


def _split_oversized_paragraph(paragraph: str, max_tokens: int) -> List[str]:
    if _estimate_tokens(paragraph) <= max_tokens:
        return [paragraph]

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
    return f"{doc_id}:chunk:{idx:04d}"


def _build_table_id(doc_id: str, idx: int) -> str:
    return f"{doc_id}:table:{idx:04d}"


def chunk_markdown_with_tables(
    markdown_text: str,
    doc_id: str,
    min_tokens: int = 300,
    max_tokens: int = 800,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
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


def build_doc_id(filename: str) -> str:
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]
