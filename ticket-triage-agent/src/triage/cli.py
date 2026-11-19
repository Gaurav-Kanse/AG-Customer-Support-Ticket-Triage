"""Command line interface with an interactive approval checkpoint."""

import argparse
import json

from triage.graph import execute_action, run_ticket


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--ticket", required=True)
    r.add_argument("--id", default="CLI-1")
    r.add_argument("--auto-approve", action="store_true", help="Local demo/test convenience")
    a = p.parse_args()
    state = run_ticket({"id": a.id, "text": a.ticket})
    print(
        json.dumps(
            {
                "classification": state["classification"],
                "evidence": state["evidence"],
                "draft": state["draft"],
                "proposed_action": state["proposed_action"],
            },
            indent=2,
        )
    )
    if a.auto_approve:
        answer = "y"
    else:
        answer = input("Approve proposed action? [y]es / [e]dit / [n]o: ").strip().lower()
    if answer == "y":
        state["approval"] = {"approved": True, "action": state["proposed_action"]}
    elif answer == "e":
        edited = input("Edited reply: ")
        state["approval"] = {"approved": True, "action": "send", "edited_text": edited}
    else:
        print("No action executed; approval was not granted.")
        print(json.dumps(state["trace"], indent=2))
        return
    print(json.dumps(execute_action(state), indent=2))


if __name__ == "__main__":
    main()
