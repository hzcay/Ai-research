from typing import Protocol, List, Optional
from src.domain.entities.document import Document, Chunk, IngestionJob

class DocumentRepositoryPort(Protocol):
    async def create_document(self, document: Document) -> Document:
        ...

    async def update_document(self, document: Document) -> Document:
        ...

    async def get_document(self, doc_id: str) -> Optional[Document]:
        ...

    async def create_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        ...

    async def update_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        ...

    async def get_ingestion_job(self, job_id: str) -> Optional[IngestionJob]:
        ...

    async def create_chunks(self, chunks: List[Chunk]) -> None:
        ...

    async def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        ...

    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        ...
