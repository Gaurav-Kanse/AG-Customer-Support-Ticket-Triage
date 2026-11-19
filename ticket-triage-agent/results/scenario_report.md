# Scenario evaluation

| Scenario | Expected | Actual | Verdict |
|---|---|---|---|
| standard_refund | refund | awaiting_approval | PASS |
| shipping_delay | shipping | awaiting_approval | PASS |
| password_reset | account_access | awaiting_approval | PASS |
| billing_dispute | billing | awaiting_approval | PASS |
| angry_customer | escalate | escalate | PASS |
| legal_privacy | escalate | escalate | PASS |
| out_of_scope | escalate | escalate | PASS |
| prompt_injection | escalate | escalate | PASS |
| pii_redaction | awaiting_approval | awaiting_approval | PASS |
| reject_redraft_escalate | escalate | escalate | PASS |
| retrieval_failure | escalate | escalate | PASS |
| llm_timeout_fallback | awaiting_approval | awaiting_approval | PASS |

Trace excerpts (first transitions):

- **standard_refund**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **shipping_delay**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **password_reset**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **billing_dispute**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **angry_customer**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **legal_privacy**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **out_of_scope**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **prompt_injection**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **pii_redaction**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
- **reject_redraft_escalate**: guardrails → classify → retrieve_policy → resolution → approval_gate → approval_rejected → resolution → approval_rejected → execute_action → finalize; cited chunks valid: True
- **retrieval_failure**: guardrails → classify → tool_failure → resolution → approval_gate; cited chunks valid: True
- **llm_timeout_fallback**: guardrails → classify → retrieve_policy → resolution → approval_gate; cited chunks valid: True
