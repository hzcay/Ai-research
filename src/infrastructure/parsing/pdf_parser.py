from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.infrastructure.parsing.docling_parser import parse_pdf_batch


class PdfParser:
    """Infrastructure adapter for PDF -> structured document parsing."""

    def parse_batch(self, pdf_paths: List[Path]) -> List[Dict[str, Any]]:
        return parse_pdf_batch(pdf_paths)
