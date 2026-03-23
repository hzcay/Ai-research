from __future__ import annotations

from typing import Any, Dict, List

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


class GenerateAnswerUseCase:
    def __init__(
        self,
        llm: LlmPort,
        retrieve: RetrieveContextUseCase,
    ) -> None:
        self._llm = llm
        self._retrieve = retrieve

    def execute(self, query: str) -> Dict[str, Any]:
        search_queries = self._llm.multi_query_rewrite(original_query=query)

        all_chunks: List[RetrievedChunk] = []
        seen_ids: set[str] = set()
        for s_query in search_queries:
            if not s_query.strip():
                continue
            new_chunks = self._retrieve.execute(s_query)
            for chunk in new_chunks:
                if chunk.id not in seen_ids:
                    all_chunks.append(chunk)
                    seen_ids.add(chunk.id)

        full_context = self._build_context(all_chunks)

        final_answer = self._llm.generate(
            user_prompt=f"CONTEXT:\n{full_context}\n\nQUESTION: {query}",
            system_instruction=SYSTEM_INSTRUCTION,
        )

        return {
            "answer": final_answer,
            "contexts": [self._chunk_to_dict(c) for c in all_chunks],
        }

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
