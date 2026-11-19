"""Provider agnostic language model interface."""

from typing import Protocol


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str: ...
