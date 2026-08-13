from src.application.use_cases.generate_answer import GenerateAnswerUseCase
from src.domain.entities.retrieval import RetrievedChunk


def test_citation_contains_stable_source_provenance() -> None:
    chunk = RetrievedChunk(
        id="parent-1",
        doc_id="doc-1",
        score=0.91,
        text="Grounded evidence.",
        page_start=3,
        page_end=4,
        metadata={
            "filename": "paper.pdf",
            "source_block_id": "parent-1",
            "matched_chunk_id": "child-2",
            "source_content_hash": "a" * 64,
            "section_path": "Results",
        },
    )

    citation = GenerateAnswerUseCase._build_citations([chunk])[0]

    assert citation["doc_id"] == "doc-1"
    assert citation["page_start"] == 3
    assert citation["page_end"] == 4
    assert citation["source_block_id"] == "parent-1"
    assert citation["matched_chunk_id"] == "child-2"
    assert citation["source_content_hash"] == "a" * 64
    assert citation["section"] == "Results"
