# KB-WPL-01.5 — Knowledge Linking Skill

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.5 |
| **Status** | **READY** — frozen candidate non-executable Skill |
| **Skill** | `ms.skill.knowledge_linking` v0.1.0 |
| **Depends on** | KB-WPL-01.3C (frozen WPL), KB-WPL-01.4 (Engineering Skills) |

## 1. Executive verdict

**READY.** Native Knowledge Linking Skill analyzes bounded metadata and produces a
reviewable Knowledge Linking Report. Links are proposed — never applied. No filesystem,
database, or graph mutation.

## 2. Package identity

| Field | Value |
|-------|-------|
| Package hash | `95a3ff6d7f83f2e6437b4fb724c9aec13b814be2ae8fdfbc94a5e3872d32602a` |
| executable | false |
| production_eligible | false |
| runtime_authorized | false |
| freeze_status | frozen_candidate |

## 3.1 Legacy module governance

- `app/knowledge/knowledge_linking/` — **authoritative** validation contour for this Skill.
- `app/knowledge/linking/` — **legacy**; do not add new imports; removal deferred to KB-WPL-01.9 or dedicated cleanup.
- Live Registry API not connected; Skill remains metadata-driven until Knowledge Core Persistence.

## 3. Shared link contracts

Package-local schemas: `KnowledgeNodeReference`, `KnowledgeLink`, `BrokenLink`,
`OrphanArtifact`, `DuplicateCandidate`, `SupersessionCandidate`, `ContradictionCandidate`,
`IndexRecommendation`, `LinkConflict`.

## 4. Detection capabilities

- Broken references (missing target, hash mismatch, stale index)
- Orphan artifacts (post-visibility filtering, standalone exemptions)
- Duplicate candidates (`merge_recommended=false` always)
- Supersession candidates (historical resolution preserved)
- Contradiction candidates (no auto-winner)
- Index recommendations (no auto-write)

## 5. Tenant boundaries

Cross-tenant links rejected with structured records. Hidden artifacts use generic
not-found behavior. Global platform-native artifacts linkable across tenants.

## 6. Methodology source

Adapted wiki-link validation methodology from external archive (`arc-obsidian-vault-linking`)
— methodology only, no Obsidian product dependency, no imported scripts.

## 7. Verification

```bash
uv run pytest tests/test_kb_wpl_01_3c_pattern_library_freeze.py -q
uv run pytest tests/test_kb_wpl_01_4_n8n_engineering_skills.py -q
uv run pytest tests/test_kb_wpl_01_5_knowledge_linking_skill.py -q
uv run ruff check app/knowledge/knowledge_linking tests/test_kb_wpl_01_5_knowledge_linking_skill.py tests/support
```

## 8. Related

- [Skill doc](../skills/ms.skill.knowledge_linking.md)
- [Freeze audit](./KB-WPL-01.5-knowledge-linking-freeze-audit.md)
- [Knowledge Core Vision](./SKILL-02-KNOWLEDGE-CORE-VISION.md)
