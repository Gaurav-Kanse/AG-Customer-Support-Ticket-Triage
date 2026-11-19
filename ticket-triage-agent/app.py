"""Single page Streamlit demo for synthetic support tickets."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import streamlit as st

from triage.graph import execute_action, run_ticket

st.set_page_config(page_title="AG-02 Ticket Triage", page_icon="🎫", layout="wide")
st.title("Customer Support Ticket Triage")
st.caption(
    "Synthetic policies · deterministic mock mode · approval required before helpdesk action"
)
samples = {
    "Refund request": "Please refund my recent purchase, I have the receipt.",
    "Shipping delay": "My package delivery is late and tracking has not updated.",
    "Password reset": "I forgot my password and cannot login.",
    "Angry customer": "I am furious, this delivery delay is unacceptable!!!",
}
choice = st.selectbox("Sample ticket", ["Custom"] + list(samples))
default = samples.get(choice, "")
text = st.text_area("Ticket text", value=default, height=130)
ticket_id = st.text_input("Ticket ID", "DEMO-001")
if st.button("Triage ticket", type="primary") and text.strip():
    st.session_state["triage_state"] = run_ticket({"id": ticket_id, "text": text})
s = st.session_state.get("triage_state")
if s:
    st.subheader("Triage result")
    a, b, c = st.columns(3)
    a.metric("Category", s["classification"]["category"])
    b.metric("Priority", s["classification"]["priority"])
    c.metric("Recommended action", s["proposed_action"])
    st.subheader("Retrieved evidence")
    for e in s["evidence"]:
        st.markdown(f"**{e['doc']} · {e['chunk_id']}** (score {e['score']:.3f})\n\n{e['text']}")
    st.subheader("Draft reply")
    edited = st.text_area("Review or edit before approval", value=s["draft"]["text"], height=130)
    left, right = st.columns(2)
    if left.button("Approve and execute"):
        s["approval"] = {"approved": True, "action": s["proposed_action"], "edited_text": edited}
        st.session_state["triage_state"] = execute_action(s)
        st.rerun()
    if right.button("Reject draft"):
        s["approval"] = {"approved": False, "action": "reject"}
        s["retry_count"] += 1
        s["escalation"] = True
        s["proposed_action"] = "escalate"
        s["action_result"] = {"status": "awaiting_approval", "external_action_executed": False}
        s["transitions"].append("reject_and_escalate")
        st.session_state["triage_state"] = s
        st.rerun()
    st.subheader("Tool and node trace")
    st.json(s["trace"])
    st.subheader("State timeline")
    st.write(" → ".join(s["transitions"]))
    if s.get("action_result"):
        st.subheader("Audit record")
        st.json(s["action_result"])
