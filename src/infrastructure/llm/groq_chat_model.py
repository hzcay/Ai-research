from __future__ import annotations

from groq import Groq

from src.application.ports.llm_port import LlmPort


class GroqChatModel(LlmPort):
    def __init__(self, api_key: str, model_name: str) -> None:
        self._client = Groq(api_key=api_key)
        self._model_name = model_name

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
