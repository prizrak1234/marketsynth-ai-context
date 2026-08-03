# KB-WPL-01.2.1 — Workflow Catalog Quality Repair

**Status:** Complete (repair pass before KB-WPL-01.2 freeze)  
**Date:** 2026-07-23  
**Depends on:** KB-WPL-01.0 intake, KB-WPL-01.1 frozen schemas, KB-WPL-01.2 parser foundation

## Scope

Repair catalog metadata quality without starting Pattern Library (01.3):

- capability classification false positives
- provider vs node-type taxonomy
- human approval structural signals
- strict `reusable_pattern_candidate` gate
- security metric reconciliation
- deduplication diagnostics
- scoped ruff gate

## Root causes fixed

| Issue | Root cause | Fix |
|-------|------------|-----|
| `workflow_documentation` on 248/248 | Sticky Note auto-tagged as documentation capability | Sticky notes → `documentation_quality` signal only |
| `workflow_backup` inflated | Substring `backup` matched inside sticky note text | Backup requires explicit name + node/operation evidence |
| Generic node types in `providers` | `extract_provider()` used node suffix as provider | `extract_integrated_providers()` with denylist |
| `human_approval` on 150 | IF/Wait/Switch treated as approval | `approval_signal_strength` + structural gate |
| 62 weak candidates | `capability != other && no code` rule | `candidate_eligibility.py` strict gate with reasons/blockers |
| Security count confusion | Mixed finding vs workflow vs node counts | Layered metrics in `security_summary.json` |

## Capability repair rules

### Sticky Notes

- Set `documentation_quality`: `none | minimal | present | substantial`
- Do **not** assign `workflow_documentation` from sticky presence alone

### workflow_documentation

Requires workflow name/description signal **and** documentation node or export action.

### workflow_backup

Requires backup intent in name/description **and** n8n export / storage node, or explicit n8n operation.

### human_approval

Only when `approval_signal_strength` is `probable` or `explicit` (HITL tool, approve/reject path, explicit markers). IF/Wait alone → `weak`, no capability.

## Provider taxonomy

Three separate layers in statistics sidecar:

| Field | Contents |
|-------|----------|
| `providers` | External services (Google Sheets, Gmail, Telegram, OpenAI, …) |
| `node_types` | Full n8n node type identifiers |
| `functional_classes` | trigger, transform, branch, aggregate, delay, transport, database, AI, publication, storage, human_review, code, other |

Denied from providers: stickyNote, code, set, if, merge, wait, httpRequest, webhook, scheduleTrigger, formTrigger.

## Candidate gate

`reusable_pattern_candidate` requires:

- valid export, canonical/unique, meaningful topology
- no critical/security blockers (destructive, shell, exposed secrets, high-risk community)
- sufficient capability/priority confidence
- `manual_audit_required=true` always
- sensitive workflows (publication/billing/PII) allowed only with explicit review reasons, never auto-production

Metadata sidecar fields per workflow:

- `candidate_reasons[]`
- `candidate_blockers[]`
- `priority_reasons[]`
- `priority_confidence`
- `capability_confidence`

## Security statistics

Explicit layers:

- `total_findings` — aggregated finding instances
- `affected_workflows_by_finding_type` — unique workflows per finding type
- `code_nodes.total_detected_nodes` — node count across catalog
- `code_nodes.affected_workflows` — workflows with code nodes

## Deduplication diagnostics

Added to `statistics.json`:

- provider-neutral / provider-aware topology collision counts
- renamed-topology candidate groups
- credential-only candidate groups
- sample-content-only candidate groups
- reason codes documenting merge policy

## Outputs rebuilt

`packages/knowledge/workflow_catalog/0.1.0/` — catalog bundle hash changed (expected; 01.2 not yet frozen).

Frozen **unchanged:** `workflow_patterns/0.1.0` schema bundle hash.

## No-execution confirmation

- No workflow execution
- No n8n import/API/network
- No Pattern Library files
- No Skills/Connectors/API/UI/DB
- Metadata-only catalog preserved

## Readiness

After owner acceptance of repaired distributions + green scoped lint → **KB-WPL-01.2 FROZEN** → KB-WPL-01.3 Pattern Library.
