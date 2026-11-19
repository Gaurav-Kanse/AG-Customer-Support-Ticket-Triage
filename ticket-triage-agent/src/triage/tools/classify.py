"""Rule-based ticket classifier tool."""

from triage.schemas import Classification, Ticket

RULES = {
    "refund": ["refund", "return", "money back"],
    "shipping": ["shipping", "delivery", "package", "tracking", "late"],
    "account_access": ["password", "login", "account", "reset"],
    "billing": ["billing", "charged", "charge", "invoice", "dispute"],
    "cancellation": ["cancel", "cancellation"],
    "privacy": ["privacy", "delete my data", "personal data", "legal", "lawyer"],
    "product_defect": ["broken", "defect", "not working", "damaged"],
    "warranty": ["warranty", "guarantee"],
}


def classify_ticket(ticket: Ticket | dict) -> Classification:
    t = Ticket.model_validate(ticket)
    s = t.text.lower()
    category = max(RULES, key=lambda k: sum(w in s for w in RULES[k]))
    hits = sum(w in s for w in RULES[category])
    if not hits:
        category = "other"
    angry = any(w in s for w in ["angry", "furious", "unacceptable", "terrible", "scam", "!!!"])
    high = any(w in s for w in ["urgent", "legal", "lawyer", "privacy", "safety", "threat"])
    return Classification(
        category=category,
        priority="urgent" if high else "high" if angry else "medium",
        sentiment="angry" if angry else "neutral",
        confidence=0.88 if hits else 0.42,
        should_escalate=category in ("privacy", "other") or angry or high,
    )
