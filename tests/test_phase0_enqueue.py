from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.ingest_pdfs import IngestPdfsUseCase
from src.domain.entities.document import Document


@pytest.fixture(autouse=True)
def run_thread_boundaries_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    async def inline(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr("src.application.use_cases.ingest_pdfs.asyncio.to_thread", inline)


@pytest.mark.asyncio
async def test_duplicate_completed_document_is_reused() -> None:
    existing = Document(id="doc-1", filename="paper.pdf", status="completed")
    repository = MagicMock()
    repository.get_document_by_content_hash = AsyncMock(return_value=existing)
    storage = MagicMock()
    queue = MagicMock()
    use_case = IngestPdfsUseCase(storage, repository, queue)

    result = await use_case.execute(b"same bytes", "paper.pdf")

    assert result["status"] == "duplicate"
    assert result["doc_id"] == "doc-1"
    storage.upload_bytes.assert_not_called()


@pytest.mark.asyncio
async def test_enqueue_failure_is_persisted_for_reconciliation() -> None:
    repository = MagicMock()
    repository.get_document_by_content_hash = AsyncMock(return_value=None)
    repository.create_document_with_job = AsyncMock()
    repository.update_ingestion_job = AsyncMock()
    storage = MagicMock()
    storage.bucket_name = "ai-research"
    queue = MagicMock()
    queue.enqueue_job = AsyncMock(side_effect=ConnectionError("redis down"))
    use_case = IngestPdfsUseCase(storage, repository, queue)

    result = await use_case.execute(b"new bytes", "paper.pdf")

    assert result["status"] == "queued"
    persisted_job = repository.update_ingestion_job.await_args.args[0]
    assert persisted_job.status == "enqueue_failed"
    assert "redis down" in persisted_job.error_message
