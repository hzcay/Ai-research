from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any, Dict, List, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter

def _estimate_tokens(text: str) -> int:
    words = len(re.findall(r"\S+", text))
    return max(1, int(words * 1.3))

def build_doc_id(filename: str) -> str:
    return hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]

def chunk_markdown_with_tables(
    markdown_text: str,
    doc_id: str,
    min_tokens: int = 300, # Legacy param, not strictly used for max thresholds now
    max_tokens: int = 800, # Legacy param
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Revised Parent-Child Chunker using Langchain's RecursiveCharacterTextSplitter.
    Returns: (parent_chunks, child_chunks)
    Note: table_chunks are merged or handled via the recursive splitter natively.
    """
    
    # 1. Create Splitters
    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000 * 4, # Approx 4 chars per token -> 8000 chars
        chunk_overlap=200 * 4,
        length_function=len,
        separators=["\n\n## ", "\n\n### ", "\n\n", "\n", ".", " "]
    )
    
    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400 * 4, # Approx 4 chars per token -> 1600 chars
        chunk_overlap=60 * 4, # 15% overlap
        length_function=len,
        separators=["\n\n", "\n", ".", " "]
    )
    
    # 2. Split into Parent Chunks
    parent_texts = parent_splitter.split_text(markdown_text)
    
    parent_chunks: List[Dict[str, Any]] = []
    child_chunks: List[Dict[str, Any]] = []
    
    for p_idx, p_text in enumerate(parent_texts):
        parent_id = str(uuid.uuid4())
        
        parent_chunks.append({
            "chunk_id": parent_id,
            "parent_id": parent_id, # Self reference for parent
            "chunk_type": "parent",
            "doc_id": doc_id,
            "text": p_text.strip(),
            "token_estimate": _estimate_tokens(p_text),
            "page_start": None, # Could extract if we map from PyMuPDF
            "page_end": None,
            "section": None # Could extract using Regex on headers
        })
        
        # 3. Split Parent into Child Chunks
        c_texts = child_splitter.split_text(p_text)
        for c_idx, c_text in enumerate(c_texts):
            child_id = str(uuid.uuid4())
            child_chunks.append({
                "chunk_id": child_id,
                "parent_id": parent_id,
                "chunk_type": "child",
                "doc_id": doc_id,
                "text": c_text.strip(),
                "token_estimate": _estimate_tokens(c_text),
                "page_start": None,
                "page_end": None,
                "section": None
            })
            
    return parent_chunks, child_chunks


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

