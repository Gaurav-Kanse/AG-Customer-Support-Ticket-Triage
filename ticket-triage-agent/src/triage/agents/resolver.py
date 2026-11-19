"""Resolution agent."""

from triage.tools.drafting import draft_reply


class ResolutionAgent:
    def run(self, text, evidence, category):
        return draft_reply(text, evidence, category)
