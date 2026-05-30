from __future__ import annotations

from pathlib import Path
from typing import List

from src.infrastructure.indexing.document_indexer import DocumentIndexer
from src.infrastructure.parsing.pdf_parser import PdfParser


class IngestPdfsUseCase:
    def __init__(self, indexer: DocumentIndexer) -> None:
        self._indexer = indexer

    async def execute(self, pdf_paths: List[Path]) -> None:
        for path in pdf_paths:
            file_bytes = path.read_bytes()
            filename = path.name
            await self._indexer.ingest_pdf_bytes(file_bytes, filename)
