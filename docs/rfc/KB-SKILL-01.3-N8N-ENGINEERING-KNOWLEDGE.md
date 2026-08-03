# n8n Engineering Knowledge — KB-SKILL-01.3

| Field | Value |
|-------|-------|
| **Program** | KB-SKILL-01.3 |
| **Status** | Candidate — non-executable |
| **Source archives** | `_Скиллы для передачи.zip`, `Боты в базу знаний.rar` (methodology only) |

---

## Objective

Adapt external n8n methodology into three native Marketsynth Skills. **No workflow deployment.**

| Skill | Package | Role |
|-------|---------|------|
| Workflow Architecture | `ms.skill.n8n_workflow_architecture` | Requirements, node boundaries, data contracts |
| Workflow Debugging | `ms.skill.n8n_workflow_debugging` | Failure localization, sandbox plans |
| Deployment Review | `ms.skill.n8n_deployment_review` | Readiness review — no PUT/POST to n8n |

All packages: **v0.1.0**, **candidate**, **executable: false**.

---

## Adapted methodology

From external references (static audit only):

- One workflow — one project folder
- Source-controlled workflow JSON
- Plan before build; sandbox for expensive debugging
- Preserve credentials during deployment (review only — no token handling)
- Explicit production settings and workflow ID verification
- Sticky Note documentation for purpose and boundaries
- Separate main agent from tool workflows
- Explicit error workflow and idempotency handling
- Human approval for publication/write actions

Provider-version notes are marked **requires_reverification** — not timeless facts.

---

## Hard boundaries

- No n8n API calls
- No workflow activation
- No credential binding from imported JSON
- No execution of archive Python scripts
- Workflow JSON remains **catalog_only** in quarantine

---

## Related

- [WORKFLOW-CAPABILITY-MAP.md](../architecture/WORKFLOW-CAPABILITY-MAP.md)
- [external-archives README](../research/external-archives/README.md)
- [KB-SKILL-01-INTEGRATED-FREEZE-AUDIT.md](KB-SKILL-01-INTEGRATED-FREEZE-AUDIT.md)
