"""Ticket workflow, backed by LangGraph when it is available.

The approval step is a hard gate: execute_action checks an explicit approved value, even
when called directly. External integrations are deliberately represented by a local mock.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from triage.agents.classifier import ClassifierAgent
from triage.agents.escalation import EscalationAgent
from triage.agents.resolver import ResolutionAgent
from triage.agents.retriever import RetrievalAgent
from triage.config import TRACE_DIR
from triage.guardrails import has_injection, redact_pii
from triage.schemas import Ticket
from triage.tools.helpdesk import Helpdesk


def _log(state, node, summary, tool=None, error=None, start=None):
    state.setdefault("trace", []).append(
        {
            "node": node,
            "input_summary": summary,
            "output_summary": "ok" if not error else "failed",
            "tool": tool,
            "latency_ms": round((time.perf_counter() - start) * 1000, 3) if start else 0,
            "error": error,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    state.setdefault("transitions", []).append(node)


def _trace_updates(state):
    return {"trace": state["trace"], "transitions": state["transitions"]}


def _initial_state(ticket: str | dict) -> dict[str, Any]:
    parsed = Ticket.model_validate(ticket if isinstance(ticket, dict) else {"id": "T-LOCAL", "text": ticket})
    return {
        "ticket": parsed.model_dump(),
        "trace": [],
        "transitions": [],
        "errors": [],
        "retry_count": 0,
        "escalation": False,
    }


def _run_local(ticket, approval=None, store=None, retriever=None, timeout=False) -> dict[str, Any]:
    """Compatibility runner used only when LangGraph cannot be imported."""
    state = _initial_state(ticket)
    ticket = state["ticket"]
    start = time.perf_counter()
    state["sanitized_text"] = redact_pii(ticket["text"])
    state["injection_flag"] = has_injection(ticket["text"])
    _log(state, "guardrails", "ticket text", start=start)
    try:
        start = time.perf_counter()
        state["classification"] = ClassifierAgent().run(
            {"id": ticket["id"], "text": state["sanitized_text"]}
        ).model_dump()
        _log(state, "classify", "sanitized ticket", "classify_ticket", start=start)
        start = time.perf_counter()
        state["evidence"] = (retriever or RetrievalAgent()).run(state["sanitized_text"])
        state["evidence"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in state["evidence"]]
        _log(state, "retrieve_policy", "sanitized ticket", "search_policy", start=start)
    except Exception as e:  # noqa: BLE001 - tool failures must fail closed to escalation
        state["errors"].append(f"{type(e).__name__}: {e}")
        state["evidence"] = []
        state["classification"] = {
            "category": "other", "priority": "high", "sentiment": "neutral",
            "confidence": 0.0, "should_escalate": True,
        }
        _log(state, "tool_failure", "fallback to escalation", "search_policy", str(e))
    state["escalation"] = EscalationAgent().run(
        _Obj(state["classification"]), state["evidence"], state["injection_flag"]
    )
    if timeout:
        state["errors"].append("LLMTimeout: deterministic fallback used")
    start = time.perf_counter()
    state["draft"] = ResolutionAgent().run(
        state["sanitized_text"], state["evidence"], state["classification"]["category"]
    ).model_dump()
    _log(state, "resolution", "policy evidence", "draft_reply", start=start)
    if state["injection_flag"]:
        state["escalation"] = True
    state["proposed_action"] = "escalate" if state["escalation"] else "send"
    state["approval"] = approval or {"approved": False, "action": "pending"}
    _log(state, "approval_gate", "await human approval", "interrupt", start=time.perf_counter())
    if state["approval"].get("approved") is True:
        return execute_action(state, store=store)
    state["action_result"] = {"status": "awaiting_approval", "external_action_executed": False}
    _persist(state)
    return state


class _Obj:
    def __init__(self, d):
        self.__dict__.update(d)


def reject_draft(state: dict) -> dict:
    """Record a human rejection, redraft once, then route repeated rejection to escalation."""
    state["retry_count"] = state.get("retry_count", 0) + 1
    _log(state, "approval_rejected", "human rejected draft", "approval_gate")
    if state["retry_count"] >= 2:
        state["escalation"] = True
        state["proposed_action"] = "escalate"
        return state
    start = time.perf_counter()
    state["draft"] = ResolutionAgent().run(
        state["sanitized_text"], state["evidence"], state["classification"]["category"]
    ).model_dump()
    _log(state, "resolution", "redraft after rejection", "draft_reply", start=start)
    state["approval"] = {"approved": False, "action": "pending"}
    state["action_result"] = {"status": "awaiting_approval", "external_action_executed": False}
    return state


def execute_action(state: dict, store=None) -> dict:
    """Run consequential mock action only after explicit human approval."""
    if state.get("approval", {}).get("approved") is not True:
        raise PermissionError("Human approval is required before any action")
    action = state["approval"].get("action")
    if action not in ("send", "escalate"):
        raise ValueError("Approval action must be send or escalate")
    text = state["approval"].get("edited_text") or state["draft"]["text"]
    if action == "send":
        text = redact_pii(text)
    start = time.perf_counter()
    state["action_result"] = (store or Helpdesk()).perform(state["ticket"]["id"], action, text)
    _log(state, "execute_action", action, "helpdesk_api", start=start)
    _log(state, "finalize", "audit recorded", start=time.perf_counter())
    _persist(state)
    return state


def _persist(state):
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    with (TRACE_DIR / f"{state['ticket']['id']}.jsonl").open("a") as f:
        for item in state["trace"]:
            f.write(json.dumps(item) + "\n")


try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command

    from triage.state import TriageState

    LANGGRAPH_AVAILABLE = True
except ImportError:
    MemorySaver = StateGraph = START = END = Command = TriageState = None
    LANGGRAPH_AVAILABLE = False


def _route(state):
    decision = EscalationAgent().run(
        _Obj(state["classification"]), state.get("evidence", []), state.get("injection_flag", False)
    )
    return "escalation_agent" if decision else "resolution_agent"


def build_graph(store=None, retriever=None, timeout=False):
    """Build a checkpointed LangGraph workflow; use the local runner as import fallback."""
    if not LANGGRAPH_AVAILABLE:
        return _run_local

    def guardrails(state):
        ticket = state["ticket"]
        start = time.perf_counter()
        result = {
            "sanitized_text": redact_pii(ticket["text"]),
            "injection_flag": has_injection(ticket["text"]),
        }
        _log(state, "guardrails", "ticket text", start=start)
        result.update(_trace_updates(state))
        return result

    def classify_retrieve(state):
        updated = {}
        try:
            start = time.perf_counter()
            updated["classification"] = ClassifierAgent().run(
                {"id": state["ticket"]["id"], "text": state["sanitized_text"]}
            ).model_dump()
            _log(state, "classify", "sanitized ticket", "classify_ticket", start=start)
            start = time.perf_counter()
            evidence = (retriever or RetrievalAgent()).run(state["sanitized_text"])
            updated["evidence"] = [e.model_dump() if hasattr(e, "model_dump") else e for e in evidence]
            _log(state, "retrieve_policy", "sanitized ticket", "search_policy", start=start)
        except Exception as e:  # noqa: BLE001 - tool failures must fail closed to escalation
            errors = list(state.get("errors", []))
            errors.append(f"{type(e).__name__}: {e}")
            updated.update(
                errors=errors,
                evidence=[],
                classification={
                    "category": "other", "priority": "high", "sentiment": "neutral",
                    "confidence": 0.0, "should_escalate": True,
                },
            )
            _log(state, "tool_failure", "fallback to escalation", "search_policy", str(e))
        if timeout:
            updated["errors"] = list(updated.get("errors", state.get("errors", [])))
            updated["errors"].append("LLMTimeout: deterministic fallback used")
        updated.update(_trace_updates(state))
        return updated

    def escalation_agent(state):
        return {"escalation": True}

    def resolution_agent(state):
        start = time.perf_counter()
        draft = ResolutionAgent().run(
            state["sanitized_text"], state["evidence"], state["classification"]["category"]
        ).model_dump()
        _log(state, "resolution", "policy evidence", "draft_reply", start=start)
        result = {"draft": draft}
        result.update(_trace_updates(state))
        return result

    def approval_gate(state):
        escalation = state.get("escalation", False) or state["injection_flag"]
        proposed = "escalate" if escalation else "send"
        _log(state, "approval_gate", "await human approval", "interrupt", start=time.perf_counter())
        approval = state.get("approval") or {"approved": False, "action": "pending"}
        result = {}
        if state.get("injection_flag"):
            result["escalation"] = True
        result["proposed_action"] = proposed
        result["approval"] = approval
        if approval.get("approved") is not True:
            result["action_result"] = {
                "status": "awaiting_approval", "external_action_executed": False
            }
        result.update(_trace_updates(state))
        return result

    def run_action(state):
        # execute_action performs its own authorization check even if the graph is misrouted.
        return execute_action(dict(state), store=store)

    def after_gate(state):
        return "execute_action" if state.get("approval", {}).get("approved") is True else END

    graph = StateGraph(TriageState)
    graph.add_node("guardrails", guardrails)
    graph.add_node("classify_retrieve", classify_retrieve)
    graph.add_node("escalation_agent", escalation_agent)
    graph.add_node("resolution_agent", resolution_agent)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("execute_action", run_action)
    graph.add_edge(START, "guardrails")
    graph.add_edge("guardrails", "classify_retrieve")
    graph.add_conditional_edges("classify_retrieve", _route)
    graph.add_edge("escalation_agent", "resolution_agent")
    graph.add_edge("resolution_agent", "approval_gate")
    graph.add_conditional_edges("approval_gate", after_gate)
    graph.add_edge("execute_action", END)
    return graph.compile(checkpointer=MemorySaver(), interrupt_before=["approval_gate"])


def run_ticket(ticket, approval=None, store=None, retriever=None, timeout=False) -> dict[str, Any]:
    """Run a ticket and pause at the checkpoint until a supplied approval is resumed."""
    if not LANGGRAPH_AVAILABLE:
        return _run_local(ticket, approval, store, retriever, timeout)
    graph = build_graph(store=store, retriever=retriever, timeout=timeout)
    config = {"configurable": {"thread_id": f"{Ticket.model_validate(ticket if isinstance(ticket, dict) else {'id': 'T-LOCAL', 'text': ticket}).id}-{uuid.uuid4()}"}}
    graph.invoke(_initial_state(ticket), config)
    snapshot = graph.get_state(config)
    if approval is not None and snapshot.next:
        graph.update_state(config, {"approval": approval})
        graph.invoke(None, config)
        snapshot = graph.get_state(config)
    state = dict(snapshot.values)
    if snapshot.next and approval is None:
        if state.get("injection_flag"):
            state["escalation"] = True
        state["proposed_action"] = "escalate" if state.get("escalation") else "send"
        state["approval"] = {"approved": False, "action": "pending"}
        _log(state, "approval_gate", "await human approval", "interrupt", start=time.perf_counter())
        _persist(state)
    if "action_result" not in state:
        state["action_result"] = {"status": "awaiting_approval", "external_action_executed": False}
    return state
