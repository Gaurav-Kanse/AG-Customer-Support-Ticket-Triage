"""Idempotent JSON-backed mock helpdesk; no external side effects."""

import json
from pathlib import Path

from triage.config import STORE_PATH


class Helpdesk:
    def __init__(self, path: Path = STORE_PATH):
        self.path = path

    def _load(self):
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def perform(self, ticket_id: str, action: str, text: str = "") -> dict:
        db = self._load()
        key = f"{ticket_id}:{action}"
        if key not in db:
            db[key] = {
                "ticket_id": ticket_id,
                "action": action,
                "text": text,
                "status": "completed",
                "history": ["created"],
            }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(db, indent=2))
        return db[key]
