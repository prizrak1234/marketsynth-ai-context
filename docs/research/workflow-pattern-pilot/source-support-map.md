# Source support map — KB-WPL-01.3A.1

Location: `packages/knowledge/workflow_patterns/0.1.0/pilot_source_support_map.json`

## Purpose

Each pilot pattern includes **pattern-specific supporting_signals** linking catalog workflow
metadata to architectural rules — without storing raw n8n bodies.

## Multi-pattern overlap (documented, not rejected)

| Workflow | Patterns supported | Distinct signals |
|----------|-------------------|------------------|
| wf-febea81827b8ad6b | human_approval_before_publication, draft_to_human_approval | switch/pre-publication vs moderator draft gate |
| wf-353be45a7de607a0 | structured_LLM_to_API_request, lead_capture_to_qualification | openAi structured stage vs batch qualification loop |
| wf-b6e1676935a48901 | retry_with_idempotency, error_workflow_or_recovery | wait/retry segment vs failure detection branch |

## Signal fields

Each signal includes:

- `source_workflow_id`
- `signal_type` (approval_gate, retry_structure, structured_output, …)
- `node_or_functional_class` (catalog node type or functional class — not raw node body)
- `topology_location` (abstract segment name)
- `supported_pattern_rule`
- `confidence` (explicit | probable)
- `limitations`
- `evidence_hash` (deterministic hash of signal identity fields)

## Single-source policy (frozen for 01.3B)

Documented in `app/knowledge/workflow_patterns/contracts.py` as `SINGLE_SOURCE_POLICY`.

Current pilot preserves **two workflow sources** per pattern; single-source expansion in 01.3B
requires PracticeRecord + complete support map + signed audit.
