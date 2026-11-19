"""Run all local evaluation scenarios and the labelled synthetic ticket set."""

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from metrics import binary_metrics
from scenarios import SCENARIOS

from triage.agents.retriever import RetrievalAgent
from triage.graph import execute_action, reject_draft, run_ticket
from triage.tools.classify import classify_ticket

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
(RESULTS / "traces").mkdir(parents=True, exist_ok=True)


def main():
    dataset = [
        json.loads(x)
        for x in (ROOT / "data/tickets_eval.jsonl").read_text().splitlines()
        if x.strip()
    ]
    true = []
    pred = []
    pr_true = []
    pr_pred = []
    ret1 = ret3 = 0
    reports = []
    lat = defaultdict(list)
    toolcounts = Counter()
    search = RetrievalAgent()
    for row in dataset:
        tic = {"id": row["id"], "text": row["text"]}
        c = classify_ticket(tic)
        true.append(row["category"])
        pred.append(c.category)
        pr_true.append(row["priority"])
        pr_pred.append(c.priority)
        ev = search.run(row["text"])
        docs = [e.doc for e in ev]
        ret1 += bool(docs and docs[0] == row["expected_policy_doc"])
        ret3 += row["expected_policy_doc"] in docs
        s = run_ticket(tic)
        reports.append(s)
        for t in s["trace"]:
            lat[t["node"]].append(t["latency_ms"])
            if t["tool"]:
                toolcounts[t["tool"]] += 1
    n = len(dataset)
    classes = sorted(set(true))
    per = {}
    for cls in classes:
        tp = sum(a == cls and b == cls for a, b in zip(true, pred))
        fp = sum(a != cls and b == cls for a, b in zip(true, pred))
        fn = sum(a == cls and b != cls for a, b in zip(true, pred))
        p = tp / (tp + fp) if tp + fp else 0
        r = tp / (tp + fn) if tp + fn else 0
        per[cls] = {
            "precision": p,
            "recall": r,
            "f1": 2 * p * r / (p + r) if p + r else 0,
            "support": sum(a == cls for a in true),
        }
    acc = sum(a == b for a, b in zip(true, pred)) / n
    macro = sum(x["f1"] for x in per.values()) / len(per)
    esc_true = [x["should_escalate"] for x in dataset]
    esc_pred = [
        classify_ticket({"id": x["id"], "text": x["text"]}).should_escalate for x in dataset
    ]
    scenario_results = []
    for i, (name, text, expect) in enumerate(SCENARIOS, 1):
        retriever = None
        if name == "retrieval_failure":

            class Broken:
                def run(self, text):
                    raise RuntimeError("injected retrieval failure")

            retriever = Broken()
        state = run_ticket(
            {"id": f"SCENARIO-{i:02d}", "text": text},
            retriever=retriever,
            timeout=name == "llm_timeout_fallback",
        )
        if name == "reject_redraft_escalate":
            state = reject_draft(state)
            state = reject_draft(state)
            state["approval"] = {"approved": True, "action": "escalate"}

            class InMemoryHelpdesk:
                def perform(self, ticket_id, action, text):
                    return {"ticket_id": ticket_id, "action": action, "status": "completed"}

            state = execute_action(state, store=InMemoryHelpdesk())
        actual = "escalate" if state.get("escalation") else state["action_result"]["status"]
        if expect == "escalate":
            passed = bool(state.get("escalation"))
        elif expect == "awaiting_approval":
            passed = state["action_result"]["status"] == "awaiting_approval"
        else:
            passed = True
        cited = state["draft"]["citations"]
        validids = {e["chunk_id"] for e in state["evidence"]}
        citation_ok = all(c in validids for c in cited)
        row = {
            "scenario": name,
            "expected": expect,
            "actual": actual,
            "passed": passed,
            "citation_correct": citation_ok,
            "transitions": state["transitions"],
            "trace": state["trace"],
        }
        scenario_results.append(row)
        (RESULTS / "traces" / f"{state['ticket']['id']}.jsonl").write_text(
            "".join(json.dumps(t) + "\n" for t in state["trace"])
        )
    # per-node latency stats over dataset graph runs
    latency = {
        k: {
            "mean_ms": statistics.mean(v),
            "p95_ms": sorted(v)[max(0, int(0.95 * len(v)) - 1)],
            "calls": len(v),
        }
        for k, v in lat.items()
    }
    metrics = {
        "dataset_size": n,
        "classification": {
            "accuracy": acc,
            "macro_f1": macro,
            "per_class": per,
            "priority_accuracy": sum(a == b for a, b in zip(pr_true, pr_pred)) / n,
        },
        "retrieval": {"hit_at_1": ret1 / n, "hit_at_3": ret3 / n},
        "escalation": binary_metrics(esc_true, esc_pred),
        "scenarios": {
            "count": len(scenario_results),
            "passed": sum(r["passed"] for r in scenario_results),
            "safety_gate_compliance": sum(
                not (
                    any(t["node"] == "execute_action" for t in r["trace"])
                    and r["expected"] != "escalate"
                )
                for r in scenario_results
            )
            / len(scenario_results),
            "citation_correctness": sum(r["citation_correct"] for r in scenario_results)
            / len(scenario_results),
        },
        "latency": latency,
        "tool_calls": dict(toolcounts),
        "notes": "Rule-based mock evaluation on synthetic data; these measurements do not establish real-world generalization. Groundedness is assessed by citation provenance, not semantic entailment.",
    }
    (RESULTS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    table = "| Scenario | Expected | Actual | Verdict |\n|---|---|---|---|\n" + "".join(
        f"| {r['scenario']} | {r['expected']} | {r['actual']} | {'PASS' if r['passed'] else 'FAIL'} |\n"
        for r in scenario_results
    )
    (RESULTS / "scenario_report.md").write_text(
        "# Scenario evaluation\n\n"
        + table
        + "\nTrace excerpts (first transitions):\n\n"
        + "".join(
            f"- **{r['scenario']}**: {' → '.join(r['transitions'])}; cited chunks valid: {r['citation_correct']}\n"
            for r in scenario_results
        )
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = classes
    mat = [[sum(a == x and b == y for a, b in zip(true, pred)) for y in labels] for x in labels]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.imshow(mat, cmap="Blues")
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, str(mat[i][j]), ha="center", va="center")
    fig.tight_layout()
    fig.savefig(RESULTS / "figures" / "confusion_matrix.png", dpi=150)
    plt.close(fig)
    print(
        json.dumps(
            {
                "classification_accuracy": acc,
                "macro_f1": macro,
                "priority_accuracy": metrics["classification"]["priority_accuracy"],
                "retrieval_hit1": ret1 / n,
                "retrieval_hit3": ret3 / n,
                "escalation": metrics["escalation"],
                "scenario_passed": metrics["scenarios"]["passed"],
                "scenario_count": len(scenario_results),
                "safety_gate_compliance": metrics["scenarios"]["safety_gate_compliance"],
                "citation_correctness": metrics["scenarios"]["citation_correctness"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
