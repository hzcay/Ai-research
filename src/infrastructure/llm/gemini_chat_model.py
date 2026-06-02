from __future__ import annotations

import math
import time
from typing import List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.application.ports.llm_port import LlmPort


class GeminiChatModel(LlmPort):
    def __init__(
        self,
        api_key: str,
        model_name: str,
        timeout_s: float = 30.0,
        retries: int = 2,
    ) -> None:
        self._model_name = model_name
        self._retries = max(0, retries)
        self._timeout_s = timeout_s
        self._client = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            timeout=timeout_s,
            max_retries=retries,
        )

    def _extract_text(self, content: str | list) -> str:
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            return "".join(texts)
        return str(content or "")

    def generate(self, user_prompt: str, system_instruction: str | None = None) -> str:
        messages = []
        if system_instruction:
            messages.append(SystemMessage(content=system_instruction))
        messages.append(HumanMessage(content=user_prompt))

        response = self._chat_with_retry(messages)
        return self._extract_text(response.content)

    def multi_query_rewrite(self, original_query: str | None = None) -> list[str]:
        if not (original_query and original_query.strip()):
            return [original_query.strip()] if original_query else [""]

        prompt = f"""You are an AI Search Expert. Your goal is to expand the user's query into 3 distinct variations to optimize Vector Database retrieval.
    
        - Variation 1 (Technical): Correct any typos and use formal, domain-specific academic terminology.
        - Variation 2 (Step-back): A high-level, conceptual question that captures the broader context or underlying principles.
        - Variation 3 (Keyword-heavy): A query focused on key entities, specific models, and technical keywords.

        Original Query: {original_query}

        RULES:
        - Provide exactly 3 lines.
        - Each line contains one query variation.
        - No numbering, no introductory text, no bullet points.
        - Maintain the language of the original query unless it's a technical term."""
        
        messages = [HumanMessage(content=prompt)]
        response = self._chat_with_retry(messages)

        raw = self._extract_text(response.content).strip()
        queries = raw.split("\n")
        cleaned = [q.strip() for q in queries if q.strip()][:3]
        return cleaned or [original_query.strip()]

    def _chat_with_retry(self, messages: list) -> any:
        for attempt in range(self._retries + 1):
            try:
                return self._client.invoke(messages)
            except Exception:
                if attempt >= self._retries:
                    raise
                time.sleep(0.2 * math.pow(2, attempt))
        raise RuntimeError("Unreachable retry state")
