from __future__ import annotations

from groq import Groq

from src.application.ports.llm_port import LlmPort


class GroqChatModel(LlmPort):
    def __init__(self, api_key: str, model_name: str, model_name_2: str) -> None:
        self._client = Groq(api_key=api_key)
        self._model_name = model_name
        self._model_name_2 = model_name_2

    def generate(self, user_prompt: str, system_instruction: str | None = None) -> str:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": user_prompt})

        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
        )
        return response.choices[0].message.content or ""

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
        
        response = self._client.chat.completions.create(
            model=self._model_name_2,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = (response.choices[0].message.content or "").strip()
        queries = raw.split("\n")
        cleaned = [q.strip() for q in queries if q.strip()][:3]
        return cleaned or [original_query.strip()]