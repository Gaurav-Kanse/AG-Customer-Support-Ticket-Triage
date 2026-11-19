"""Evidence-grounded reply drafting."""

from triage.schemas import Draft


def draft_reply(text: str, evidence: list, category: str) -> Draft:
    if not evidence:
        return Draft(
            text="I could not verify guidance for this issue. I am escalating this for a specialist review.",
            citations=[],
            abstained=True,
        )
    ev = evidence[0] if isinstance(evidence[0], dict) else evidence[0].model_dump()
    if ev["score"] < 0.04:
        return Draft(
            text="I could not verify guidance for this issue. I am escalating this for a specialist review.",
            citations=[],
            abstained=True,
        )
    return Draft(
        text=f"Thanks for contacting us about {category.replace('_', ' ')}. {ev['text']} Please reply if you need further help. [Source: {ev['chunk_id']}]",
        citations=[ev["chunk_id"]],
    )
