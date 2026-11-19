"""Graph state shape."""

from typing import Any, TypedDict


class TriageState(TypedDict, total=False):
    ticket: dict[str, str]
    sanitized_text: str
    injection_flag: bool
    classification: dict[str, Any]
    evidence: list[dict[str, Any]]
    draft: dict[str, Any]
    approval: dict[str, Any]
    action_result: dict[str, Any]
    trace: list[dict[str, Any]]
    transitions: list[str]
    errors: list[str]
    retry_count: int
    escalation: bool
    proposed_action: str
    timeout: bool
