# CURSOR_AUDIT_PLAYBOOK.md

**Project:** Marketsynth  
**Document Type:** AI Audit Playbook  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from `AI_DEVELOPMENT_RULES.md`

---

# 1. Purpose

This document tells Cursor or another AI coding agent how to audit the Marketsynth governance core.

---

# 2. Audit Input

Auditor MUST inspect:

- `PROJECT_CONSTITUTION.md`
- `PROJECT_INDEX.md`
- all documents under `docs/architecture`
- all documents under `docs/runtime`
- all documents under `docs/domain`
- all documents under `docs/engineering`
- all documents under `docs/contracts`
- all documents under `docs/governance`
- all documents under `docs/knowledge`
- all documents under `docs/security`
- all documents under `docs/migration`

---

# 3. Audit Questions

Auditor MUST check:

1. Does any document contradict the Constitution?
2. Does any document treat BotFazer v3 as Source of Truth?
3. Is Human Approval always required before Real Execution?
4. Is Readiness clearly separated from Approval?
5. Is Knowledge Candidate prohibited from crossing tenant boundary?
6. Are tenant boundaries preserved in every model?
7. Are Orchestrator limits clear?
8. Are Supervisor limits clear?
9. Is Programmer Agent write restriction clear?
10. Are contracts protected from silent mutation?
11. Are secrets excluded from prompts/logs/errors/evidence/docs?
12. Can future HR/Legal/Finance domains be added without global rewrite?
13. Can Cursor understand the reading order?
14. Are FROZEN documents protected by governance?
15. Are missing documents clearly identified?

---

# 4. Audit Output Format

Auditor SHOULD return:

```markdown
# Marketsynth Core Audit Report

## Verdict
PASS / PASS WITH PATCHES / FAIL

## Critical Findings
## Major Findings
## Minor Findings
## Missing Documents
## Contradictions
## Recommended Patches
## Final Decision
```

---

# 5. Pass Criteria

PASS requires:

- no critical contradictions;
- no approval bypass;
- no tenant boundary ambiguity;
- no knowledge boundary conflict;
- clear AI reading order;
- clear legacy migration policy.

---

# 6. Audit Status

PASSED.

This document is FROZEN v1.0.0.
