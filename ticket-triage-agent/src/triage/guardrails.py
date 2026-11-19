"""PII handling and untrusted-content screening."""

import re

EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[A-Z]{2,}\b")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
INJECTION = re.compile(
    r"(?i)ignore (?:all )?(?:previous|prior) instructions|reveal (?:the )?system prompt|bypass (?:the )?policy|refund me regardless"
)


def redact_pii(text: str) -> str:
    text = CARD.sub("[REDACTED_CARD]", text)
    text = EMAIL.sub("[REDACTED_EMAIL]", text)
    return PHONE.sub("[REDACTED_PHONE]", text)


def has_injection(text: str) -> bool:
    return bool(INJECTION.search(text))
