"""Classifier agent."""

from triage.tools.classify import classify_ticket


class ClassifierAgent:
    def run(self, ticket):
        return classify_ticket(ticket)
