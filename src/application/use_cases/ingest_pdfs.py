from __future__ import annotations

from pathlib import Path
from typing import List

from src.infrastructure.indexing.document_indexer import DocumentIndexer
from src.infrastructure.parsing.pdf_parser import PdfParser


class IngestPdfsUseCase:
    def __init__(self, parser: PdfParser, indexer: DocumentIndexer) -> None:
        self._parser = parser
        self._indexer = indexer

    def execute(self, pdf_paths: List[Path]) -> None:
        docs = self._parser.parse_batch(pdf_paths)
        self._indexer.index(docs)
