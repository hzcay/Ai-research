from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_with_mocked_use_case(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    mock_uc = MagicMock()
    mock_uc.execute = AsyncMock()
    mock_uc.execute.return_value = {
        "answer": "Mocked answer for testing.",
        "citations": [],
        "debug": {
            "retrieval_mode": "hybrid",
            "cache_hit": False,
            "embedding_ms": 1.0,
            "retrieval_ms": 1.0,
            "llm_ms": 1.0,
            "total_ms": 3.0,
            "top_k": 0,
        },
    }
    monkeypatch.setattr(
        "src.api.routes.chat.get_generate_answer_use_case",
        lambda: mock_uc,
    )

    response = client.post(
        "/chat/",
        json={"query": "What is RAG?", "auto_expand_corpus": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Mocked answer for testing."
    assert body["citations"] == []
    assert body["debug"]["retrieval_mode"] == "hybrid"
    mock_uc.execute.assert_called_once()
    call_kw = mock_uc.execute.call_args
    assert call_kw[0][0] == "What is RAG?"


def test_search_with_mocked_retrieval(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    mock_ret = MagicMock()
    mock_ret.execute = AsyncMock(return_value=([], {}))

    monkeypatch.setattr(
        "src.api.routes.search.get_retrieve_context_use_case",
        lambda: mock_ret,
    )

    response = client.post(
        "/search/",
        json={"query": "machine learning", "top_k": 5},
    )

    assert response.status_code == 200
    assert response.json() == {"results": []}
    mock_ret.execute.assert_called_once()


def test_upload_rejects_non_pdf_content(client: TestClient) -> None:
    response = client.post(
        "/ingest/upload",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File content is not a valid PDF."
