from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from src.infrastructure.config.settings import get_settings
from src.infrastructure.database.models import Document as DBDocument, Chunk as DBChunk, IngestionJob as DBIngestionJob
from src.domain.entities.document import Document, Chunk, IngestionJob
from typing import List, Optional

settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class PostgresRepository:
    def __init__(self):
        self.async_session = async_session_factory
        
    def _to_db_doc(self, doc: Document) -> DBDocument:
        return DBDocument(
            id=doc.id,
            filename=doc.filename,
            minio_path=doc.minio_path,
            markdown_path=doc.markdown_path,
            status=doc.status,
            created_at=doc.created_at,
            metadata_=doc.metadata_
        )
        
    def _to_domain_doc(self, db_doc: DBDocument) -> Document:
        return Document(
            id=db_doc.id,
            filename=db_doc.filename,
            minio_path=db_doc.minio_path,
            markdown_path=db_doc.markdown_path,
            status=db_doc.status,
            created_at=db_doc.created_at,
            metadata_=db_doc.metadata_
        )

    def _to_db_job(self, job: IngestionJob) -> DBIngestionJob:
        return DBIngestionJob(
            id=job.id,
            doc_id=job.doc_id,
            status=job.status,
            created_at=job.created_at
        )
        
    def _to_domain_job(self, db_job: DBIngestionJob) -> IngestionJob:
        return IngestionJob(
            id=db_job.id,
            doc_id=db_job.doc_id,
            status=db_job.status,
            created_at=db_job.created_at
        )

    def _to_db_chunk(self, chunk: Chunk) -> DBChunk:
        return DBChunk(
            chunk_id=chunk.chunk_id,
            doc_id=chunk.doc_id,
            parent_id=chunk.parent_id,
            chunk_type=chunk.chunk_type,
            text_content=chunk.text_content,
            chunk_index=chunk.chunk_index,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            token_count=chunk.token_count,
            content_hash=chunk.content_hash,
            embedding_status=chunk.embedding_status,
            created_at=chunk.created_at
        )

    def _to_domain_chunk(self, db_chunk: DBChunk) -> Chunk:
        return Chunk(
            chunk_id=db_chunk.chunk_id,
            doc_id=db_chunk.doc_id,
            parent_id=db_chunk.parent_id,
            chunk_type=db_chunk.chunk_type,
            text_content=db_chunk.text_content,
            chunk_index=db_chunk.chunk_index,
            page_start=db_chunk.page_start,
            page_end=db_chunk.page_end,
            token_count=db_chunk.token_count,
            content_hash=db_chunk.content_hash,
            embedding_status=db_chunk.embedding_status,
            created_at=db_chunk.created_at
        )

    async def create_document(self, document: Document) -> Document:
        async with self.async_session() as session:
            db_doc = self._to_db_doc(document)
            session.add(db_doc)
            await session.commit()
            return document

    async def update_document(self, document: Document) -> Document:
        async with self.async_session() as session:
            stmt = select(DBDocument).where(DBDocument.id == document.id)
            result = await session.execute(stmt)
            db_doc = result.scalar_one_or_none()
            if db_doc:
                db_doc.filename = document.filename
                db_doc.minio_path = document.minio_path
                db_doc.markdown_path = document.markdown_path
                db_doc.status = document.status
                db_doc.metadata_ = document.metadata_
                await session.commit()
            return document

    async def get_document(self, doc_id: str) -> Optional[Document]:
        async with self.async_session() as session:
            stmt = select(DBDocument).where(DBDocument.id == doc_id)
            result = await session.execute(stmt)
            db_doc = result.scalar_one_or_none()
            if db_doc:
                return self._to_domain_doc(db_doc)
            return None

    async def create_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        async with self.async_session() as session:
            db_job = self._to_db_job(job)
            session.add(db_job)
            await session.commit()
            return job

    async def update_ingestion_job(self, job: IngestionJob) -> IngestionJob:
        async with self.async_session() as session:
            stmt = select(DBIngestionJob).where(DBIngestionJob.id == job.id)
            result = await session.execute(stmt)
            db_job = result.scalar_one_or_none()
            if db_job:
                db_job.status = job.status
                await session.commit()
            return job

    async def get_ingestion_job(self, job_id: str) -> Optional[IngestionJob]:
        async with self.async_session() as session:
            stmt = select(DBIngestionJob).where(DBIngestionJob.id == job_id)
            result = await session.execute(stmt)
            db_job = result.scalar_one_or_none()
            if db_job:
                return self._to_domain_job(db_job)
            return None
            
    async def create_chunks(self, chunks: List[Chunk]):
        async with self.async_session() as session:
            db_chunks = [self._to_db_chunk(c) for c in chunks]
            session.add_all(db_chunks)
            await session.commit()
            
    async def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Chunk]:
        async with self.async_session() as session:
            stmt = select(DBChunk).where(DBChunk.chunk_id.in_(chunk_ids))
            result = await session.execute(stmt)
            db_chunks = result.scalars().all()
            return [self._to_domain_chunk(c) for c in db_chunks]
            
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        async with self.async_session() as session:
            stmt = select(DBChunk).where(DBChunk.chunk_id == chunk_id)
            result = await session.execute(stmt)
            db_chunk = result.scalar_one_or_none()
            if db_chunk:
                return self._to_domain_chunk(db_chunk)
            return None

