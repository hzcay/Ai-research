from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.process_document import ProcessDocumentUseCase
from src.domain.entities.document import Document
from src.infrastructure.indexing.chunker import chunk_document_pages


def test_page_chunks_are_deterministic_and_keep_provenance() -> None:
    pages = [
        {"page_number": 1, "text": "# Introduction\n\nA stable source block."},
        {"page_number": 2, "text": "# Method\n\nA second source block."},
    ]

    first_parents, first_children = chunk_document_pages(pages, "doc-1")
    second_parents, second_children = chunk_document_pages(pages, "doc-1")

    assert [c["chunk_id"] for c in first_parents] == [
        c["chunk_id"] for c in second_parents
    ]
    assert [c["chunk_id"] for c in first_children] == [
        c["chunk_id"] for c in second_children
    ]
    assert first_parents[0]["page_start"] == 1
    assert first_parents[0]["section"] == "Introduction"
    assert len(first_parents[0]["source_content_hash"]) == 64
    assert first_children[0]["parent_id"] == first_parents[0]["chunk_id"]


@pytest.mark.asyncio
async def test_process_document_persists_and_indexes_before_completion() -> None:
    document = Document(
        id="doc-1",
        filename="paper.pdf",
        minio_path="s3://ai-research/raw/paper.pdf",
        status="queued",
    )
    repository = MagicMock()
    repository.get_document = AsyncMock(return_value=document)
    repository.update_document = AsyncMock()
    repository.create_chunks = AsyncMock()
    repository.delete_chunks_by_document = AsyncMock()

    storage = MagicMock()
    storage.get_object.return_value = b"%PDF mock"
    parser = MagicMock()
    parser.parse_document.return_value = {
        "source": "test",
        "content": "# Result\n\nGrounded result.",
        "total_pages": 1,
        "metadata": {"title": "Paper"},
        "pages": [{"page_number": 1, "text": "# Result\n\nGrounded result."}],
    }
    vector_store = MagicMock()
    vector_store.upsert_chunks.side_effect = lambda chunks: len(chunks)

    use_case = ProcessDocumentUseCase(
        document_repo=repository,
        storage_port=storage,
        parse_port=parser,
        embedder=MagicMock(),
        vector_store=vector_store,
    )

    await use_case.execute("doc-1")

    assert repository.create_chunks.await_count == 2
    stored = repository.create_chunks.await_args_list[0].args[0]
    assert {chunk.chunk_type for chunk in stored} == {"parent", "child"}
    assert stored[0].page_start == 1
    completed_write = repository.create_chunks.await_args_list[-1].args[0]
    assert all(
        chunk.embedding_status == "completed"
        for chunk in completed_write
        if chunk.chunk_type == "child"
    )
    assert document.status == "completed"
    assert document.markdown_path is not None
    assert repository.update_document.await_count == 2


@pytest.mark.asyncio
async def test_process_document_fails_when_vector_index_is_incomplete() -> None:
    document = Document(
        id="doc-2",
        filename="paper.pdf",
        minio_path="s3://ai-research/raw/paper.pdf",
        status="queued",
    )
    repository = MagicMock()
    repository.get_document = AsyncMock(return_value=document)
    repository.update_document = AsyncMock()
    repository.create_chunks = AsyncMock()
    repository.delete_chunks_by_document = AsyncMock()
    storage = MagicMock()
    storage.get_object.return_value = b"%PDF mock"
    parser = MagicMock()
    parser.parse_document.return_value = {
        "source": "test",
        "content": "Evidence text",
        "pages": [{"page_number": 1, "text": "Evidence text"}],
    }
    vector_store = MagicMock()
    vector_store.upsert_chunks.return_value = 0
    use_case = ProcessDocumentUseCase(
        document_repo=repository,
        storage_port=storage,
        parse_port=parser,
        embedder=MagicMock(),
        vector_store=vector_store,
    )

    with pytest.raises(RuntimeError, match="Qdrant indexed"):
        await use_case.execute("doc-2")

    assert document.status == "failed"


@pytest.mark.asyncio
async def test_process_document_falls_back_when_page_text_is_empty() -> None:
    document = Document(
        id="scan-1",
        filename="scan.pdf",
        minio_path="s3://ai-research/raw/scan.pdf",
    )
    repository = MagicMock()
    repository.get_document = AsyncMock(return_value=document)
    repository.update_document = AsyncMock()
    repository.create_chunks = AsyncMock()
    repository.delete_chunks_by_document = AsyncMock()
    storage = MagicMock()
    storage.get_object.return_value = b"%PDF scanned"
    parser = MagicMock()
    parser.parse_document.return_value = {
        "source": "docling",
        "content": "# OCR result\n\nText recovered by OCR.",
        "pages": [{"page_number": 1, "text": ""}],
    }
    vector_store = MagicMock()
    vector_store.upsert_chunks.side_effect = lambda chunks: len(chunks)
    use_case = ProcessDocumentUseCase(
        document_repo=repository,
        storage_port=storage,
        parse_port=parser,
        embedder=MagicMock(),
        vector_store=vector_store,
    )

    await use_case.execute("scan-1")

    assert document.status == "completed"
    assert repository.create_chunks.await_count == 2
