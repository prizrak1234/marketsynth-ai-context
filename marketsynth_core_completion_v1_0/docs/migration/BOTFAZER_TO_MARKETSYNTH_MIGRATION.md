# BOTFAZER_TO_MARKETSYNTH_MIGRATION.md

**Project:** Marketsynth  
**Document Type:** Legacy Migration Specification  
**Status:** FROZEN  
**Version:** 1.0.0  
**Authority:** Derived from `PROJECT_CONSTITUTION.md`

---

# 1. Purpose

This document defines how legacy BotFazer v3 code and documentation are migrated into Marketsynth.

---

# 2. Core Law

BotFazer v3 is legacy implementation.

Marketsynth architecture is Source of Truth.

Migration direction:

```text
Marketsynth Architecture → Audit → Legacy Code → Migration Plan → Implementation
```

Never reverse this direction.

---

# 3. Legacy Classification

Legacy artifacts MAY be classified as:

- reusable as-is;
- reusable after refactor;
- reference only;
- obsolete;
- dangerous;
- unknown.

---

# 4. Migration Audit

Before reusing legacy code, audit:

- architecture compatibility;
- tenant isolation;
- approval boundary;
- execution safety;
- provider boundary;
- contract shape;
- tests;
- naming;
- security risks.

---

# 5. Naming Migration

Official future-facing name is Marketsynth.

BotFazer MAY remain only in:

- historical notes;
- migration docs;
- legacy folder names;
- commit history;
- compatibility notes.

User-facing UI and official docs MUST use Marketsynth.

---

# 6. Code Migration Rules

Code MAY be migrated only if:

- it does not violate Constitution;
- it preserves tenant isolation;
- it preserves approval boundaries;
- it does not leak secrets;
- it follows engineering layers;
- tests can be added.

---

# 7. No Forced Fit

Marketsynth architecture MUST NOT be weakened to fit legacy code.

If legacy code conflicts with architecture, code must change or be discarded.

---

# 8. Migration Phases

Recommended phases:

1. inventory;
2. architecture gap analysis;
3. risk classification;
4. extraction plan;
5. isolated refactor;
6. tests;
7. integration;
8. audit;
9. freeze.

---

# 9. Audit Status

PASSED.

This document is FROZEN v1.0.0.
