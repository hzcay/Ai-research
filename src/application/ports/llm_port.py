from __future__ import annotations

from typing import Protocol


class LlmPort(Protocol):
    def generate(self, user_prompt: str, system_instruction: str | None = None) -> str:
        ...
