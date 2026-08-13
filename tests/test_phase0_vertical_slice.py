from __future__ import annotations

from typing import Any

import pytest

from src.application.use_cases.generate_answer import GenerateAnswerUseCase
from src.application.use_cases.ingest_pdfs import IngestPdfsUseCase
from src.application.use_cases.process_document import ProcessDocumentUseCase
from src.application.use_cases.retrieve_context import RetrieveContextUseCase
from src.domain.entities.document import Chunk, Document, IngestionJob
from src.domain.entities.retrieval import RetrievedChunk


class MemoryRepository:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.jobs: dict[str, IngestionJob] = {}
        self.chunks: dict[str, Chunk] = {}

    async def get_document_by_content_hash(
        self, content_hash: str, project_id: str | None = None
    ):
        return next(
            (
                doc
                for doc in self.documents.values()
                if doc.content_hash == content_hash
                and (project_id is None or doc.project_id == project_id)
            ),
            None,
        )

    async def create_document_with_job(self, document, job):
        self.documents[document.id] = document
        self.jobs[job.doc_id] = job
        return document

    async def update_ingestion_job(self, job):
        self.jobs[job.doc_id] = job
        return job

    async def get_document(self, doc_id: str):
        return self.documents.get(doc_id)

    async def update_document(self, document):
        self.documents[document.id] = document
        return document

    async def delete_chunks_by_document(self, doc_id: str):
        self.chunks = {
            key: chunk for key, chunk in self.chunks.items() if chunk.doc_id != doc_id
        }

    async def create_chunks(self, chunks):
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk

    async def get_chunks_by_ids(self, chunk_ids):
        return [self.chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in self.chunks]


class MemoryStorage:
    bucket_name = "ai-research"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload_bytes(self, object_name: str, content: bytes) -> None:
        self.objects[object_name] = content

    def get_object(self, object_name: str) -> bytes:
        return self.objects[object_name]


class MemoryQueue:
    def __init__(self) -> None:
        self.doc_id: str | None = None

    async def enqueue_job(self, _name: str, doc_id: str, **_kwargs: Any) -> str:
        self.doc_id = doc_id
        return "queue-job-1"


class FixedParser:
    def parse_document(self, _path):
        text = "# Results\n\nThe intervention improved accuracy by 12 percent."
        return {
            "source": "phase0-test-parser",
            "content": text,
            "total_pages": 1,
            "pages": [{"page_number": 1, "text": text}],
        }


class FixedEmbedder:
    def encode_query(self, _text: str):
        return {"dense": [1.0], "sparse": {"indices": [1], "values": [1.0]}}

    def encode_documents(self, texts):
        return [self.encode_query(text) for text in texts]


class MemoryVectorStore:
    def __init__(self) -> None:
        self.chunks: list[dict[str, Any]] = []

    def delete_document(self, document_id: str) -> None:
        self.chunks = [chunk for chunk in self.chunks if chunk["doc_id"] != document_id]

    def upsert_chunks(self, chunks):
        self.chunks.extend(chunks)
        return len(chunks)

    def search(self, query_vectors, top_k, document_id=None, project_id=None):
        del query_vectors
        selected = [
            chunk
            for chunk in self.chunks
            if document_id is None or chunk["doc_id"] == document_id
            if project_id is None or chunk.get("project_id") == project_id
        ][:top_k]
        return [
            RetrievedChunk(
                id=chunk["chunk_id"],
                doc_id=chunk["doc_id"],
                score=0.99,
                text="",
                page_start=chunk.get("page_start"),
                page_end=chunk.get("page_end"),
                metadata={
                    "parent_id": chunk["parent_id"],
                    "filename": chunk["filename"],
                    "page_start": chunk.get("page_start"),
                    "page_end": chunk.get("page_end"),
                    "section_path": chunk.get("section"),
                    "source_content_hash": chunk.get("source_content_hash"),
                },
            )
            for chunk in selected
        ]


class MemoryChunkCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get_multiple_chunks(self, chunk_ids):
        return {chunk_id: self.values[chunk_id] for chunk_id in chunk_ids if chunk_id in self.values}

    def set_chunk_text(self, chunk_id: str, text: str):
        self.values[chunk_id] = text


@pytest.mark.asyncio
async def test_pdf_upload_to_retrieval_citation_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def inline(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("src.application.use_cases.ingest_pdfs.asyncio.to_thread", inline)
    monkeypatch.setattr("src.application.use_cases.process_document.asyncio.to_thread", inline)

    repository = MemoryRepository()
    storage = MemoryStorage()
    queue = MemoryQueue()
    embedder = FixedEmbedder()
    vector_store = MemoryVectorStore()

    ingest = IngestPdfsUseCase(storage, repository, queue)
    upload = await ingest.execute(b"%PDF-1.7 phase-0", "unsafe/../paper.pdf")

    assert upload["status"] == "queued"
    assert queue.doc_id == upload["doc_id"]
    assert repository.jobs[upload["doc_id"]].status == "queued"
    assert repository.documents[upload["doc_id"]].filename == "paper.pdf"

    process = ProcessDocumentUseCase(
        document_repo=repository,
        storage_port=storage,
        parse_port=FixedParser(),
        embedder=embedder,
        vector_store=vector_store,
    )
    await process.execute(upload["doc_id"])

    document = repository.documents[upload["doc_id"]]
    assert document.status == "completed"
    assert document.markdown_path
    assert vector_store.chunks

    retrieve = RetrieveContextUseCase(
        embedder=embedder,
        vector_store=vector_store,
        chunk_cache=MemoryChunkCache(),
        document_repo=repository,
    )
    chunks, _metrics = await retrieve.execute(
        "How much did accuracy improve?", document_id=document.id
    )

    assert len(chunks) == 1
    citation = GenerateAnswerUseCase._build_citations(chunks)[0]
    assert citation["doc_id"] == document.id
    assert citation["page_start"] == 1
    assert citation["source_block_id"]
    assert citation["matched_chunk_id"]
    assert len(citation["source_content_hash"]) == 64
