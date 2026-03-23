from __future__ import annotations

from typing import Any, Dict, List

from src.application.ports.llm_port import LlmPort
from src.domain.entities.retrieval import RetrievedChunk

SYSTEM_INSTRUCTION = """You are an Expert Academic Research Assistant.
Your task is to answer questions strictly based on the provided Context.

CONSTRAINTS:
1. Groundedness: If the answer is not in the Context, say: "I do not have enough information based on the provided papers."
2. Citations: Cite paper titles or authors if available in the Context.
3. Tone: Formal, objective, and academic.
4. Structure: Use bullet points for clarity."""


class GenerateAnswerUseCase:
    def __init__(self, llm: LlmPort) -> None:
        self._llm = llm

    def execute(self, query: str, chunks: List[RetrievedChunk]) -> Dict[str, Any]:
        context = self._build_context(chunks)
        prompt = f"# CONTEXT\n{context}\n\n# USER QUESTION\n{query}\n\n# RESPONSE:"
        answer = self._llm.generate(
            user_prompt=prompt,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        return {
            "answer": answer,
            "contexts": [self._chunk_to_dict(c) for c in chunks],
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
