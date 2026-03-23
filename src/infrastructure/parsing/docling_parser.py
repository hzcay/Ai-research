from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import fitz
from docling.document_converter import DocumentConverter
from src.infrastructure.parsing.parsed_writer import save_parsed

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


def _extract_title_from_markdown(markdown: str) -> str:
    m = re.search(r"^##\s+(.+)$", markdown, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        if not _title_looks_bad(title) and len(title) >= 10:
            return title
    return ""


def _extract_authors_from_markdown(markdown: str, title: str) -> List[str]:
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
        if _ARXIV_LINE_RE.search(ln):
            continue
        if len(ln) < 5 or len(ln) > 300:
            continue
        candidates.append(ln)
    if not candidates:
        return []

    raw = " ".join(candidates)
    raw = re.sub(r"[*†‡§∗]", " ", raw)
    raw = re.sub(r"(?<![A-Za-z])\d+(?:\s*,\s*\d+)*(?![A-Za-z])", " ", raw)
    raw = re.sub(r"\s{2,}", " ", raw).strip(" -,:;")

    team_hits = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]*\s+Team\b", raw)
    if team_hits:
        out_team: List[str] = []
        seen_team = set()
        for t in team_hits:
            t = t.strip()
            if t and t not in seen_team:
                seen_team.add(t)
                out_team.append(t)
        if out_team:
            return out_team

    name_re = re.compile(r"\b[A-Z][a-zA-Z'’\-]+(?:\s+[A-Z]\.)?\s+[A-Z][a-zA-Z'’\-]+\b")
    names = name_re.findall(raw)
    if names:
        out: List[str] = []
        seen = set()
        for n in names:
            n = n.strip()
            if n and n not in seen:
                seen.add(n)
                out.append(n)
        if out:
            return out
    return [raw] if raw else []


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

    title = _extract_title_from_markdown(markdown) or _extract_title_pymupdf(pdf_path) or doc.name or pdf_path.stem
    authors = _extract_authors_from_markdown(markdown, title) or _extract_authors_pymupdf(pdf_path, title) or ["Unknown"]

    abstract = _extract_abstract(markdown)
    if not abstract:
        with fitz.open(pdf_path) as fdoc:
            raw = ""
            for i in range(min(2, fdoc.page_count)):
                raw += fdoc.load_page(i).get_text("text") + "\n"
            abstract = _extract_abstract(raw)

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
        title = _extract_title_pymupdf(pdf_path) or (doc.metadata or {}).get("title", "") or pdf_path.stem
        authors = _extract_authors_pymupdf(pdf_path, title) or ["Unknown"]
        pages_text = [doc.load_page(idx).get_text("text").strip() for idx in range(doc.page_count)]
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


def parse_research_paper(path: str | Path) -> Dict[str, Any]:
    pdf_path = Path(path)
    try:
        return _parse_with_docling(pdf_path)
    except Exception as e:
        print(f"Docling failed: {e}. Falling back to PyMuPDF.")
        return _parse_with_pymupdf(pdf_path)


def parse_pdf_batch(pdf_paths: List[Path], data_dir: Path | None = None) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    if data_dir is None:
        here = Path(__file__).resolve()
        data_dir = next((p / "data" for p in [here.parent, *here.parents] if (p / "data").exists()), Path("data"))

    for pdf in pdf_paths:
        result = parse_research_paper(pdf)
        raw_path, proc_path = save_parsed(result, data_dir, pdf)
        result["raw_path"] = str(raw_path)
        result["processed_path"] = str(proc_path)
        outputs.append(result)
    return outputs
