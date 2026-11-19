"""Deterministic local mock. No pretrained model or network calls."""


class MockLLM:
    def complete(self, prompt: str) -> str:
        return "Use only the supplied policy evidence. If insufficient, abstain and escalate."
