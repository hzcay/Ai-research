from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.models import Document, Chunk, IngestionJob
from typing import List, Optional

class PostgresRepository:
    def __init__(self):
        settings = get_settings()
        self.engine = create_async_engine(settings.database_url, echo=False)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        
    async def create_document(self, document: Document) -> Document:
        async with self.async_session() as session:
            session.add(document)
            await session.commit()
            return document

    async def update_document(self, document: Document) -> Document:
        async with self.async_session() as session:
            session.add(document)
            await session.commit()
            return document

    async def get_document(self, doc_id: str) -> Optional[Document]:
        async with self.async_session() as session:
            stmt = select(Document).where(Document.id == doc_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        async with self.async_session() as session:
            session.add(job)
            await session.commit()
            return job

    async def update_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        async with self.async_session() as session:
            session.add(job)
            await session.commit()
            return job

    async def get_ingestion_job(self, job_id: str) -> Optional[IngestionJob]:
        async with self.async_session() as session:
            stmt = select(IngestionJob).where(IngestionJob.id == job_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
            
    async def create_chunks(self, chunks: List[Chunk]):
        async with self.async_session() as session:
            session.add_all(chunks)
            await session.commit()
            
    async def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        async with self.async_session() as session:
            stmt = select(Chunk).where(Chunk.chunk_id.in_(chunk_ids))
            result = await session.execute(stmt)
            return list(result.scalars().all())
            
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        async with self.async_session() as session:
            stmt = select(Chunk).where(Chunk.chunk_id == chunk_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
