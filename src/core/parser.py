from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import fitz
from docling.document_converter import DocumentConverter

MAX_SANE_TITLE_LEN = 200
MIN_SANE_ABSTRACT_LEN = 80
_QUOTE_CHARS = set('""\u2018\u2019\u201C\u201D\u00AB\u00BB\u2039\u203A')
_ARXIV_LINE_RE = re.compile(r"arXiv:\d|^\[?\w{2,4}\.\w{2,4}\]?$|\bdoi\b", re.IGNORECASE)

def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def _has_any_quote(text: str) -> bool:
    return any(ch in _QUOTE_CHARS for ch in text) or bool(
        re.search(r'[\u0022\u0027\u2018-\u201F\u00AB\u00BB]', text)
    )

def _title_looks_bad(title: str) -> bool:
    if not title or len(title) > MAX_SANE_TITLE_LEN:
        return True
    if re.match(r"arXiv:\d", title, re.IGNORECASE):
        return True
    if re.match(r"\d{4}\.\d{4,}", title):
        return True
    quote_count = sum(1 for ch in title if ch in _QUOTE_CHARS)
    if quote_count >= 2:
        return True
    if _has_any_quote(title) and len(title) > 120:
        return True
    return False


def _extract_title_pymupdf(pdf_path: Path) -> str:
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return ""

        embedded = (doc.metadata or {}).get("title", "").strip()
        if embedded and not _title_looks_bad(embedded):
            return embedded

        page_dict = doc.load_page(0).get_text("dict")
        lines_info: List[Dict[str, Any]] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                texts = [s.get("text", "").strip() for s in spans if s.get("text")]
                if not texts:
                    continue
                sizes = [float(s.get("size", 0) or 0) for s in spans]
                avg_size = sum(sizes) / max(len(sizes), 1)
                y0 = float((line.get("bbox") or [0, 0])[1])
                lines_info.append({"text": _collapse_ws(" ".join(texts)), "size": avg_size, "y0": y0})

        if not lines_info:
            return ""

        max_size = max(li["size"] for li in lines_info)
        tolerance = max_size * 0.1
        title_lines = sorted(
            [li for li in lines_info if li["size"] >= max_size - tolerance],
            key=lambda c: c["y0"],
        )
        title = " ".join(li["text"] for li in title_lines).strip()
        if _title_looks_bad(title):
            best = sorted(lines_info, key=lambda c: (-c["size"], c["y0"]))[0]
            return best["text"]
        return title


def _extract_authors_pymupdf(pdf_path: Path, title: str) -> List[str]:
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return []

        embedded = (doc.metadata or {}).get("author", "").strip()
        if embedded:
            return [a.strip() for a in re.split(r"[,;]", embedded) if a.strip()]

        page_dict = doc.load_page(0).get_text("dict")
        lines: List[Dict[str, Any]] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                texts = [s.get("text", "").strip() for s in spans if s.get("text")]
                if not texts:
                    continue
                sizes = [float(s.get("size", 0) or 0) for s in spans]
                avg_size = sum(sizes) / max(len(sizes), 1)
                y0 = float((line.get("bbox") or [0, 0])[1])
                lines.append({"text": _collapse_ws(" ".join(texts)), "size": avg_size, "y0": y0})

        if not lines:
            return []

        title_y, title_size = 0.0, 0.0
        for ln in lines:
            if ln["text"] and title and ln["text"] in title:
                title_y = ln["y0"]
                title_size = ln["size"]
                break

        below = sorted([l for l in lines if l["y0"] > title_y + 1], key=lambda x: x["y0"])
        authors: List[str] = []
        for ln in below[:8]:
            if ln["size"] < max(7.5, title_size * 0.5):
                if authors:
                    break
                continue
            txt = ln["text"]
            if len(txt) < 3:
                continue
            if re.search(r"\b(abstract|introduction|keywords)\b", txt, flags=re.IGNORECASE):
                break
            if _has_any_quote(txt) or len(txt) > 120 or _ARXIV_LINE_RE.search(txt):
                continue
            authors.append(txt)
            if len(authors) >= 3:
                break

        if len(authors) == 1 and "," in authors[0] and len(authors[0]) <= 300:
            parts = [p.strip() for p in authors[0].split(",") if p.strip()]
            if len(parts) >= 2:
                authors = parts
        return authors


def _extract_abstract(text: str) -> str:
    m = re.search(
        r"(?:^|\n)#+\s*abstract\s*\n+(.*?)(?=\n#+\s|\Z)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        candidate = _collapse_ws(m.group(1))
        if len(candidate) >= MIN_SANE_ABSTRACT_LEN:
            return candidate

    m = re.search(
        r"\babstract\b[:\.\s\-]*(.+?)(?:\b(?:introduction|1[\.\s]|keywords)\b)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        candidate = _collapse_ws(m.group(1))
        if len(candidate) >= MIN_SANE_ABSTRACT_LEN:
            return candidate
    return ""


# ---------------------------------------------------------------------------
# Markdown-based metadata extraction (from Docling output)
# ---------------------------------------------------------------------------

def _extract_title_from_markdown(markdown: str) -> str:
    """First ## heading in the markdown is typically the paper title."""
    m = re.search(r"^##\s+(.+)$", markdown, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        if not _title_looks_bad(title) and len(title) >= 10:
            return title
    return ""


def _extract_authors_from_markdown(markdown: str, title: str) -> List[str]:
    """Lines between the title heading and the next heading/section break."""
    if not title:
        return []

    escaped = re.escape(title)
    m = re.search(
        rf"^##\s+{escaped}\s*\n+(.*?)(?=\n##\s|\n<!-- |\Z)",
        markdown,
        re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []

    block = m.group(1).strip()
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]

    candidates: List[str] = []
    for ln in lines[:5]:
        if re.search(r"\b(abstract|introduction|keywords)\b", ln, re.IGNORECASE):
            break
        if ln.startswith("http") or ln.startswith("Figure") or ln.startswith("!["):
            continue
        if _has_any_quote(ln) or _ARXIV_LINE_RE.search(ln):
            continue
        if len(ln) < 5 or len(ln) > 300:
            continue
        candidates.append(ln)

    if not candidates:
        return []

    # join all candidate lines then split by comma-like separators
    raw = " ".join(candidates)
    # remove affiliation markers like superscripts/numbers/stars
    raw = re.sub(r"\s*[,\s]*\d+\s*[,\s]*", " ", raw)
    raw = re.sub(r"[*†‡§∗]", "", raw)
    raw = re.sub(r"\s{2,}", " ", raw).strip()

    # split on common author separators
    parts = re.split(r"\s{2,}|(?<=\w)\s*,\s*(?=[A-Z])", raw)
    authors = [p.strip().rstrip(",") for p in parts if len(p.strip()) >= 3]
    return authors if authors else []


_converter: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter


def _parse_with_docling(pdf_path: Path) -> Dict[str, Any]:
    converter = _get_converter()
    result = converter.convert(pdf_path)
    doc = result.document
    markdown = doc.export_to_markdown()

    # title: markdown first, then PyMuPDF fallback
    title = _extract_title_from_markdown(markdown)
    if not title:
        title = _extract_title_pymupdf(pdf_path)
    if not title:
        title = doc.name or pdf_path.stem

    # authors: markdown first, then PyMuPDF fallback
    authors = _extract_authors_from_markdown(markdown, title)
    if not authors:
        authors = _extract_authors_pymupdf(pdf_path, title)
    if not authors:
        authors = ["Unknown"]

    abstract = _extract_abstract(markdown)
    if not abstract:
        with fitz.open(pdf_path) as fdoc:
            raw = ""
            for i in range(min(2, fdoc.page_count)):
                raw += fdoc.load_page(i).get_text("text") + "\n"
            abstract = _extract_abstract(raw)

    total_pages = 0
    with fitz.open(pdf_path) as fdoc:
        total_pages = fdoc.page_count

    return {
        "filename": pdf_path.name,
        "source": "docling",
        "metadata": {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "has_tables": "|" in markdown and "---" in markdown,
        },
        "total_pages": total_pages,
        "content": markdown,
    }


def _parse_with_pymupdf(pdf_path: Path) -> Dict[str, Any]:
    with fitz.open(pdf_path) as doc:
        title = _extract_title_pymupdf(pdf_path)
        if not title:
            title = (doc.metadata or {}).get("title", "") or pdf_path.stem

        authors = _extract_authors_pymupdf(pdf_path, title)
        if not authors:
            authors = ["Unknown"]

        pages_text: List[str] = []
        for idx in range(doc.page_count):
            pages_text.append(doc.load_page(idx).get_text("text").strip())

        full_text = "\n\n".join(pages_text)
        abstract = _extract_abstract(full_text)

    return {
        "filename": pdf_path.name,
        "source": "pymupdf",
        "metadata": {
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "has_tables": False,
        },
        "total_pages": len(pages_text),
        "content": full_text,
    }

def _build_frontmatter(result: Dict[str, Any]) -> str:
    meta = result.get("metadata", {})
    title_safe = meta.get("title", "").replace('"', '\\"')
    authors = meta.get("authors", []) or []
    authors_yaml = "[" + ", ".join(f"\"{a.replace('\"', '\\\\\"')}\"" for a in authors) + "]"
    abstract_safe = meta.get("abstract", "")[:300].replace('"', '\\"')

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

    raw_dir = data_dir / "raw_texts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{stem}.md"

    pages: List[str] = []
    with fitz.open(pdf_path) as doc:
        for idx in range(doc.page_count):
            text = doc.load_page(idx).get_text("text").strip()
            pages.append(f"<!-- page {idx + 1} -->\n\n{text}")

    with raw_path.open("w", encoding="utf-8") as f:
        f.write(f"<!-- raw text: {result.get('filename')} -->\n\n")
        f.write("\n\n---\n\n".join(pages))

    proc_dir = data_dir / "processed"
    proc_dir.mkdir(parents=True, exist_ok=True)
    proc_path = proc_dir / f"{stem}.md"

    with proc_path.open("w", encoding="utf-8") as f:
        f.write(_build_frontmatter(result))
        f.write(result.get("content", ""))

    return raw_path, proc_path

def parse_research_paper(path: str | Path) -> Dict[str, Any]:
    pdf_path = Path(path)
    try:
        return _parse_with_docling(pdf_path)
    except Exception as e:
        print(f"Docling failed: {e}. Falling back to PyMuPDF.")
        return _parse_with_pymupdf(pdf_path)

if __name__ == "__main__":
    here = Path(__file__).resolve()
    repo_root = next((p for p in [here.parent, *here.parents] if (p / "data").exists()), here.parent)
    data_dir = repo_root / "data"

    pdfs = list((data_dir / "raw_pdfs").glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in data/raw_pdfs/")

    for pdf in pdfs:
        print(f"\n{'='*60}")
        print(f"File: {pdf.name}")
        data = parse_research_paper(pdf)
        meta = data.get("metadata", {})
        content = data.get("content", "")

        print(f"Source    : {data.get('source')}")
        print(f"Pages     : {data.get('total_pages')}")
        print(f"Title     : {meta.get('title', '')[:120]}")
        print(f"Authors   : {meta.get('authors', [])}")
        abstract = meta.get("abstract", "")
        print(f"Abstract  : ({len(abstract)} chars) {abstract[:200]}{'...' if len(abstract) > 200 else ''}")
        print(f"Has Tables: {meta.get('has_tables')}")
        print(f"Content   : {len(content)} chars")
        print(f"Preview   :\n{content[:500]}")

        raw_out, proc_out = save_parsed(data, data_dir, pdf)
        print(f"  -> Raw : {raw_out}")
        print(f"  -> Proc: {proc_out}")
