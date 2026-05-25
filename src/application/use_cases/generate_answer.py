from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from src.application.ports.llm_port import LlmPort
from src.application.use_cases.retrieve_context import RetrieveContextUseCase
from src.domain.entities.retrieval import RetrievedChunk

SYSTEM_INSTRUCTION = """You are an Expert Academic Research Assistant.
Your task is to answer questions strictly based on the provided Context.

CONSTRAINTS:
1. Groundedness: If the answer is not in the Context, say: "I do not have enough information based on the provided papers."
2. Citations: When using information from a source, cite it using [source_id].
3. Tone: Formal, objective, and academic.
4. Structure: Use bullet points for clarity.
5. Honesty: Do not invent citations."""

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
        start_total = time.perf_counter()
        
        search_queries = [
            s.strip()
            for s in self._llm.multi_query_rewrite(original_query=query)
            if s.strip()
        ]
        if not search_queries:
            search_queries = [query.strip()]

        def gather(did: Optional[str]) -> tuple[List[RetrievedChunk], dict]:
            acc: List[RetrievedChunk] = []
            seen: set[str] = set()
            total_embed = 0.0
            total_retrieve = 0.0
            for s_query in search_queries:
                c, m = self._retrieve.execute(s_query, top_k=top_k, document_id=did)
                total_embed += m.get("embedding_ms", 0.0)
                total_retrieve += m.get("retrieval_ms", 0.0)
                for chunk in c:
                    if chunk.id not in seen:
                        seen.add(chunk.id)
                        acc.append(chunk)
            return acc, {"embedding_ms": total_embed, "retrieval_ms": total_retrieve}

        chunks, metrics = gather(document_id)
        scope = "primary_document" if document_id else "corpus"
        
        if not chunks and document_id and auto_expand_corpus:
            chunks, metrics = gather(None)
            scope = "expanded_corpus"

        start_llm = time.perf_counter()
        result = self._answer_from_chunks(query, chunks, scope)
        
        if self._is_refusal(result["answer"]) and document_id and auto_expand_corpus:
            chunks, metrics = gather(None)
            start_llm_fallback = time.perf_counter()
            result = self._answer_from_chunks(query, chunks, "expanded_corpus")
            llm_ms = (time.perf_counter() - start_llm_fallback) * 1000
        else:
            llm_ms = (time.perf_counter() - start_llm) * 1000

        total_ms = (time.perf_counter() - start_total) * 1000
        
        result["debug"] = {
            "retrieval_mode": "hybrid",
            "cache_hit": False,
            "embedding_ms": round(metrics["embedding_ms"], 2),
            "retrieval_ms": round(metrics["retrieval_ms"], 2),
            "llm_ms": round(llm_ms, 2),
            "total_ms": round(total_ms, 2),
            "top_k": len(chunks)
        }
        
        return result

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
            "citations": self._build_citations(chunks),
            "retrieval_scope": retrieval_scope,
        }

    @staticmethod
    def _is_refusal(answer: str) -> bool:
        return REFUSAL_MARKER in answer.lower()

    @staticmethod
    def _build_context(chunks: List[RetrievedChunk]) -> str:
        parts = []
        for idx, chunk in enumerate(chunks, start=1):
            parts.append(
                f"[Source {idx}]\n"
                f"document_name: {chunk.metadata.get('filename', 'Unknown')}\n"
                f"page: {chunk.metadata.get('page')}\n"
                f"chunk_id: {chunk.id}\n"
                f"score: {chunk.score}\n\n"
                f"content:\n{chunk.text}\n"
            )
        return "\n".join(parts)

    @staticmethod
    def _build_citations(chunks: List[RetrievedChunk]) -> List[Dict[str, Any]]:
        citations = []
        for idx, chunk in enumerate(chunks, start=1):
            citations.append({
                "id": idx,
                "document_name": chunk.metadata.get("filename", "Unknown"),
                "page": chunk.metadata.get("page"),
                "chunk_id": chunk.id,
                "score": round(float(chunk.score or 0.0), 4),
                "text": chunk.text[:700]
            })
        return citations
