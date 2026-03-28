from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.ports.llm_port import LlmPort
from src.application.use_cases.retrieve_context import RetrieveContextUseCase
from src.domain.entities.retrieval import RetrievedChunk

SYSTEM_INSTRUCTION = """You are an Expert Academic Research Assistant.
Your task is to answer questions strictly based on the provided Context.

CONSTRAINTS:
1. Groundedness: If the answer is not in the Context, say: "I do not have enough information based on the provided papers."
2. Citations: Cite paper titles or authors if available in the Context.
3. Tone: Formal, objective, and academic.
4. Structure: Use bullet points for clarity."""

REFUSAL_MARKER = "i do not have enough information based on the provided papers"


class GenerateAnswerUseCase:
    def __init__(
        self,
        llm: LlmPort,
        retrieve: RetrieveContextUseCase,
    ) -> None:
        self._llm = llm
        self._retrieve = retrieve

    def execute(
        self,
        query: str,
        document_id: Optional[str] = None,
        *,
        auto_expand_corpus: bool = True,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        search_queries = [
            s.strip()
            for s in self._llm.multi_query_rewrite(original_query=query)
            if s.strip()
        ]
        if not search_queries:
            search_queries = [query.strip()]

        def gather(did: Optional[str]) -> List[RetrievedChunk]:
            acc: List[RetrievedChunk] = []
            seen: set[str] = set()
            for s_query in search_queries:
                for chunk in self._retrieve.execute(s_query, top_k=top_k, document_id=did):
                    if chunk.id not in seen:
                        seen.add(chunk.id)
                        acc.append(chunk)
            return acc

        if not document_id or not auto_expand_corpus:
            chunks = gather(document_id)
            scope = "primary_document" if document_id else "corpus"
            return self._answer_from_chunks(query, chunks, scope)
            
        narrow = gather(document_id)
        if not narrow:
            chunks = gather(None)
            return self._answer_from_chunks(query, chunks, "expanded_corpus")

        first = self._answer_from_chunks(query, narrow, "primary_document")
        if self._is_refusal(first["answer"]):
            chunks = gather(None)
            return self._answer_from_chunks(query, chunks, "expanded_corpus")
        return first

    def _answer_from_chunks(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        retrieval_scope: str,
    ) -> Dict[str, Any]:
        full_context = self._build_context(chunks)
        final_answer = self._llm.generate(
            user_prompt=f"CONTEXT:\n{full_context}\n\nQUESTION: {query}",
            system_instruction=SYSTEM_INSTRUCTION,
        )
        return {
            "answer": final_answer,
            "contexts": [self._chunk_to_dict(c) for c in chunks],
            "retrieval_scope": retrieval_scope,
        }

    @staticmethod
    def _is_refusal(answer: str) -> bool:
        return REFUSAL_MARKER in answer.lower()

    @staticmethod
    def _build_context(chunks: List[RetrievedChunk]) -> str:
        lines: List[str] = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("source", "Unknown Source")
            lines.append(f"--- Document {i} (Source: {source}) ---\n{chunk.text}\n")
        return "\n".join(lines).strip()

    @staticmethod
    def _chunk_to_dict(chunk: RetrievedChunk) -> Dict[str, Any]:
        return {
            "id": chunk.id,
            "score": chunk.score,
            "text": chunk.text,
            "metadata": chunk.metadata,
            "payload": chunk.payload,
        }
