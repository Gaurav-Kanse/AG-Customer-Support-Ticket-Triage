"""Build a compact PDF report from committed evaluation outputs (matplotlib only)."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parents[1]
m = json.loads((ROOT / "results/metrics.json").read_text())
scenarios = (ROOT / "results/scenario_report.md").read_text()
pdf = ROOT / "reports/project_report.pdf"
pages = [
    (
        "AG-02 Customer Support Ticket Triage",
        "Bleep Education internship · Agentic AI\n\nName: ____________________    Roll number: ____________________\n\nSynthetic-data MVP · Mock provider only",
    ),
    (
        "Abstract",
        "This project demonstrates a safe support ticket triage pipeline. It classifies requests, retrieves policy evidence, drafts cited responses, recommends escalation, and pauses for human approval before a mock helpdesk action. The implementation is deterministic and uses synthetic policy and ticket data.",
    ),
    (
        "Introduction and problem statement",
        "Support teams must categorize requests, find policy, respond consistently, and route sensitive or uncertain issues. Automating these steps without approval can cause unauthorized external actions. The objective is an auditable human-in-the-loop prototype.",
    ),
    (
        "Objectives and knowledge base",
        "Four specialized agents handle classification, retrieval, resolution, and escalation. The synthetic knowledge base contains policies for refunds, shipping, account access, billing, cancellation, privacy, defects, warranty, escalation, and SLA priorities.",
    ),
    (
        "Tools and architecture",
        "Python, LangGraph 1.2.23, Pydantic, scikit-learn TF-IDF, Streamlit, pytest, matplotlib. Tools: classify_ticket, search_policy, draft_reply, and JSON-backed mock helpdesk. A typed LangGraph state routes conditionally to escalation or resolution, pauses before approval with a MemorySaver checkpoint, then runs the approved mock action and audit.",
    ),
    (
        "Methodology and implementation",
        "PII redaction and injection screening precede inference. The rule classifier is deterministic; TF-IDF ranks local policy chunks. Drafts include retrieved chunk identifiers. The execute function enforces explicit approval. Node timings, transitions, and errors are recorded.",
    ),
    (
        "Testing evidence",
        f"Pytest result: 10 passed. Scenarios: {m['scenarios']['passed']}/{m['scenarios']['count']} passed. Approval compliance: {m['scenarios']['safety_gate_compliance']:.3f}. The suite tests approval enforcement in the LangGraph node and workflow, redaction, injection, retrieval, and tool failure fallback.",
    ),
    (
        "Evaluation results",
        f"40 synthetic tickets. Classification accuracy {m['classification']['accuracy']:.3f}; macro-F1 {m['classification']['macro_f1']:.3f}; priority accuracy {m['classification']['priority_accuracy']:.3f}. Retrieval hit@1 {m['retrieval']['hit_at_1']:.3f}, hit@3 {m['retrieval']['hit_at_3']:.3f}. Escalation P/R/F1: {m['escalation']['precision']:.3f}/{m['escalation']['recall']:.3f}/{m['escalation']['f1']:.3f}. Citation provenance {m['scenarios']['citation_correctness']:.3f}. These are mock-mode outcomes, not real-world generalization.",
    ),
    (
        "Challenges, limitations, conclusion, and future scope",
        "The LangGraph workflow uses an in-memory checkpoint, which does not survive process restarts. The evaluated system remains local and deterministic. The dataset is small and synthetic; retrieval hit@1 and escalation precision leave room for improvement. Next steps: use durable checkpointing, add human-reviewed policy data, strengthen semantic grounding evaluation, and integrate a real helpdesk only behind the same approval gate.",
    ),
    (
        "References and acknowledgements",
        "Synthetic policy docs authored for AG-02. Framework references: Pydantic, scikit-learn, Streamlit, pytest, matplotlib, LangGraph documentation. No pretrained LLM or external service was used.",
    ),
]
with PdfPages(pdf) as out:
    for title, body in pages:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.10, 0.91, title, fontsize=18, weight="bold", wrap=True)
        fig.text(0.10, 0.82, body, fontsize=11, va="top", wrap=True)
        fig.text(
            0.10,
            0.05,
            "AG-02 · Synthetic evaluation · Add student name and roll number before submission",
            fontsize=8,
            color="gray",
        )
        out.savefig(fig)
        plt.close(fig)
print(f"Wrote {pdf} ({len(pages)} pages)")
