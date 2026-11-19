"""Policy retrieval agent."""

from triage.tools.retrieval import PolicySearch


class RetrievalAgent:
    def __init__(self):
        self.search = PolicySearch()

    def run(self, text):
        return self.search.search_policy(text)
