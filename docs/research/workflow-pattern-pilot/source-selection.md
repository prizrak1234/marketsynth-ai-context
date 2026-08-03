# Pilot Source Selection

Selected **12 source workflows** from **35** `reusable_pattern_candidate` records.

## Selection criteria

- `manual_audit_required=true` in catalog statistics sidecar
- no unresolved critical security finding
- structural signals match target pattern (not title alone)
- prefer ≥2 sources per pattern where architecture aligns

## Selected workflows

| Workflow ID | Normalized name (truncated) | Pilot patterns |
|-------------|----------------------------|----------------|
| wf-febea81827b8ad6b | AI Content Master - Moderator | human_approval, draft_to_approval |
| wf-16b82581942c24a9 | Google Forms SEO publication | human_approval |
| wf-353be45a7de607a0 | Qualify Lead Lists (OpenAI) | structured_LLM, lead_capture |
| wf-b6c98c93d44e4384 | AI Product Research (Firecrawl) | structured_LLM |
| wf-b144bd6927caa092 | AI_Ranking_Checker | evidence_grounded |
| wf-9c87e7783b3cb118 | OpenAI RAG knowledge Q&A | evidence_grounded |
| wf-bdf26007404af6a3 | Google Maps lead scrape | lead_capture |
| wf-c7d30b91fd4e5694 | n8n backup to GitLab | workflow_backup |
| wf-21966e054442133e | Workflow backup variant | workflow_backup |
| wf-b6e1676935a48901 | Retail Payment Failure Alert | retry, error_recovery |
| wf-60870942fc4ef5b9 | Promo Code Expiry Alert | retry |
| wf-580f7458a07243a7 | API Mock Auto-Refresh | error_recovery |
| wf-de3f478cf93ab7e0 | Legal contract governance | draft_to_approval |

## Coverage matrix

| Required theme | Pattern | Sources |
|----------------|---------|---------|
| Human approval before publication | human_approval_before_publication | 2 |
| Structured LLM output validation | structured_LLM_to_API_request | 2 |
| Retry/idempotency | retry_with_idempotency | 2 |
| RAG/evidence grounding | evidence_grounded_generation | 2 |
| Lead capture → qualification | lead_capture_to_qualification | 2 |
| Draft → human approval | draft_to_human_approval | 2 |
| Workflow backup | workflow_backup | 2 |
| Error handling/recovery | error_workflow_or_recovery | 2 |

## Rationale

Selection based on catalog `categories`, `approval_signal_strength`, `functional_classes`,
`publication_actions`, and `candidate_reasons` — not workflow titles alone.
