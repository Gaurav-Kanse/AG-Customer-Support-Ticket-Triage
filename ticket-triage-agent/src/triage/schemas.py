"""Validated inputs and outputs used across the triage system."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal[
    "refund",
    "shipping",
    "account_access",
    "billing",
    "cancellation",
    "privacy",
    "product_defect",
    "warranty",
    "other",
]
Priority = Literal["low", "medium", "high", "urgent"]


class Ticket(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class Classification(BaseModel):
    category: Category
    priority: Priority
    sentiment: Literal["calm", "neutral", "angry"]
    confidence: float = Field(ge=0, le=1)
    should_escalate: bool


class Evidence(BaseModel):
    doc: str
    chunk_id: str
    text: str
    score: float


class Draft(BaseModel):
    text: str
    citations: list[str]
    abstained: bool = False


class Approval(BaseModel):
    approved: bool
    action: Literal["send", "escalate", "reject"]
    edited_text: str | None = None
