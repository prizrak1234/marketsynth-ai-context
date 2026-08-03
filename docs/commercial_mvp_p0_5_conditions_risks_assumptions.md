# Commercial MVP P0.5 — Conditions, risks, assumptions

## Conditions (mainly CONDITIONAL_GO)

id, title, required_action, owner_role, success_criterion, evidence_required, milestone/deadline, consequence_if_unmet, status (`open|in_progress|satisfied|failed|waived`).  
Waiver requires explicit `waiver_note`. No auto-tasks.

## Risks

title, description, severity, probability (bounded enums — no percentages), business_consequence, linked Evidence, mitigation, verdict_sensitivity, status.

## Assumptions

statement, reason_required, linked Evidence, confidence, validation method/stage, impact_if_false, status.  
Missing Evidence must not silently become an assumption.

## Change triggers

Describe possible transitions; occurrence requires review — never silently mutate approved verdicts.
