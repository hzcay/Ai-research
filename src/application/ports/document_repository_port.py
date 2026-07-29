from typing import Protocol, List, Optional
from src.domain.entities.document import Document, Chunk, IngestionJob

class DocumentRepositoryPort(Protocol):
    async def create_document(self, document: Document) -> Document:
        ...

    async def update_document(self, document: Document) -> Document:
        ...

    async def get_document(self, doc_id: str) -> Optional[Document]:
        ...

    async def get_document_by_content_hash(self, content_hash: str) -> Optional[Document]:
        ...

    async def create_document_with_job(
        self, document: Document, job: IngestionJob
    ) -> Document:
        ...

    async def create_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        ...

    async def update_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        ...

    async def get_ingestion_job(self, job_id: str) -> Optional[IngestionJob]:
        ...

    async def get_ingestion_job_by_doc_id(self, doc_id: str) -> Optional[IngestionJob]:
        ...

    async def list_ingestion_jobs_by_status(
        self, statuses: List[str]
    ) -> List[IngestionJob]:
        ...

    async def create_chunks(self, chunks: List[Chunk]) -> None:
        ...

    async def delete_chunks_by_document(self, doc_id: str) -> None:
        ...

    async def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        ...

    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        ...
