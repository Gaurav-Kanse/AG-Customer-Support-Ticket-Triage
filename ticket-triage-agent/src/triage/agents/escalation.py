"""Escalation decision agent."""


class EscalationAgent:
    def run(self, classification, evidence, injection=False):
        first = evidence[0] if evidence else {}
        score = first.get("score", 0.0) if isinstance(first, dict) else first.score
        return bool(
            classification.should_escalate
            or injection
            or not evidence
            or score < 0.04
            or classification.confidence < 0.5
        )
