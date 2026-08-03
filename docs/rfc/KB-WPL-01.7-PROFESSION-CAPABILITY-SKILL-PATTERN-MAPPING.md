# KB-WPL-01.7 — Profession / Capability / Skill / Pattern Mapping

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.7 |
| **Status** | **READY** — frozen candidate mapped read-only model |
| **Bundle** | `packages/knowledge/capability_model/0.1.0/` |
| **Depends on** | KB-WPL-01.3C (WPL), KB-WPL-01.4–01.6 (Skills) |

## 1. Executive verdict

**READY.** Canonical hierarchy frozen:

**Profession → Capability → Skill → Workflow Pattern → Connector → Tool**

Four professions mapped with 49 capabilities, real Skill bindings, all 20 frozen Workflow
Patterns, conceptual Connector/Tool classes, dependency graphs, readiness model, and
explicit capability gaps. No orchestration, runtime, persistence, API, or UI.

## 2. Bundle identity

| Field | Value |
|-------|-------|
| bundle_hash | `e1e2bbeb025a3348944a5dab43e5661d31e2ac559e9e8de4989836c50831e42b` |
| semantic_bundle_hash | `20fbd1b9f2e4f4f6f044622e37734824a406c727adff8fb97541266a15bbd633` |
| bundle_status | `mapped_read_only_model` |
| freeze_status | `frozen_candidate` |
| runtime_authorized | false |
| production_eligible | false |

## 3. Professions

| profession_id | Name | Capabilities |
|---------------|------|--------------|
| `profession.ai_marketing_director` | AI Marketing Director | 17 marketing |
| `profession.automation_architect` | Automation Architect | 12 engineering |
| `profession.knowledge_architect` | Knowledge Architect | 11 knowledge |
| `profession.content_deliverables_architect` | Content & Deliverables Architect | 8 deliverables |

## 4. Binding rules

- Mapping does **not** grant permissions.
- Mapping does **not** activate Skills or Connectors.
- Capability readiness ≠ production readiness.
- Missing implementation remains explicit in gap register.

## 5. Verification

```bash
uv run pytest tests/test_kb_wpl_01_6_presentation_architecture_skill.py -q
uv run pytest tests/test_kb_wpl_01_7_capability_mapping.py -q
uv run ruff check app/knowledge/capability_model tests/test_kb_wpl_01_7_capability_mapping.py tests/support
```

## 6. Next queue

| Phase | Deliverable |
|-------|-------------|
| KB-WPL-01.8 | Knowledge Discovery Read Models | ✅ Complete |
| KB-WPL-01.9 | Integrated Freeze Audit | Pending |

## 7. Related

- [Architecture map](../architecture/PROFESSION-CAPABILITY-SKILL-PATTERN-MAP.md)
- [Gap register](../architecture/CAPABILITY-GAP-REGISTER.md)
