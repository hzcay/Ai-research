from __future__ import annotations

from typing import List, Protocol


class LlmPort(Protocol):
    def generate(self, user_prompt: str, system_instruction: str | None = None) -> str:
        ...

    def multi_query_rewrite(self, original_query: str | None = None) -> List[str]:
        ...
