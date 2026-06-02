from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import fitz


def build_frontmatter(result: Dict[str, Any]) -> str:
    meta = result.get("metadata", {})
    title_safe = str(meta.get("title", "")).replace('"', '\\"')
    authors = meta.get("authors", []) or []
    escaped_authors = ['"' + str(a).replace('"', '\\"') + '"' for a in authors]
    authors_yaml = "[" + ", ".join(escaped_authors) + "]"
    abstract_safe = str(meta.get("abstract", ""))[:300].replace('"', '\\"')

    return (
        "---\n"
        f'title: "{title_safe}"\n'
        f"authors: {authors_yaml}\n"
        f"source: {result.get('source', 'unknown')}\n"
        f"total_pages: {result.get('total_pages', 0)}\n"
        f"has_tables: {str(meta.get('has_tables', False)).lower()}\n"
        f'abstract: "{abstract_safe}"\n'
        "---\n\n"
    )


def save_parsed(result: Dict[str, Any], data_dir: Path, pdf_path: Path) -> Tuple[Path, Path]:
    stem = Path(result.get("filename", "unknown")).stem
    debug_dir = data_dir / "debug" / stem
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    pages: List[str] = []
    with fitz.open(pdf_path) as doc:
        for idx in range(doc.page_count):
            text = doc.load_page(idx).get_text("text").strip()
            pages.append(f"<!-- page {idx + 1} -->\n\n{text}")
            
    raw_path = debug_dir / "raw_content.md"
    raw_path.write_text(
        f"<!-- raw text: {result.get('filename')} -->\n\n" + "\n\n---\n\n".join(pages),
        encoding="utf-8",
    )

    proc_path = debug_dir / "cleaned_content.md"
    proc_path.write_text(build_frontmatter(result) + str(result.get("content", "")), encoding="utf-8")
    return raw_path, proc_path
