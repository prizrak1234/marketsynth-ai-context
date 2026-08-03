# Engineering Skill Matrix (n8n / Workflow)

Separate from the core marketing Skill sequence (SKILL-02). These Skills consume the
frozen Workflow Pattern Library as read-only knowledge. Profession/Capability mapping:
[PROFESSION-CAPABILITY-SKILL-PATTERN-MAP.md](../architecture/PROFESSION-CAPABILITY-SKILL-PATTERN-MAP.md).

| Skill ID | Version | Status | Executable | output_contract_type |
|----------|---------|--------|------------|----------------------|
| `ms.skill.n8n_workflow_architecture` | 0.1.0 | candidate | false | research |
| `ms.skill.n8n_workflow_debugging` | 0.1.0 | candidate | false | research |
| `ms.skill.n8n_deployment_review` | 0.1.0 | candidate | false | research |
| `ms.skill.knowledge_linking` | 0.1.0 | frozen candidate | false | research |
| `ms.skill.presentation_architecture` | 0.1.0 | frozen candidate | false | research |

## Knowledge dependencies

| Skill | Frozen WPL semantic hash | Catalog hash |
|-------|--------------------------|--------------|
| All three | `1ddd0d033f6028bd5dcf5ee555186c6be0389a96459615b6221348783d9b1883` | `5389c3a7fe77a8625e4cceab76da79ee33b816437a671d05a1dac969da1365fa` |

## Capability split

| Skill | Designs | Diagnoses | Reviews deployment | Links metadata | Presentation spec | Executes |
|-------|---------|-----------|-------------------|----------------|---------------------|----------|
| Architecture | ✅ | — | — | — | — | ❌ |
| Debugging | — | ✅ | — | — | — | ❌ |
| Deployment Review | — | — | ✅ | — | — | ❌ |
| Knowledge Linking | — | — | — | ✅ | — | ❌ |
| Presentation Architecture | — | — | — | — | ✅ | ❌ |

## Cross-package flow

Architecture output (`architecture_id`) may be consumed by Deployment Review input.
Debugging `regression_test_plan` may become Deployment Review test evidence.
No Skill executes another; no runtime engine exists.

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_4_n8n_engineering_skills.py -q
uv run pytest tests/test_kb_wpl_01_5_knowledge_linking_skill.py -q
uv run pytest tests/test_kb_wpl_01_6_presentation_architecture_skill.py -q
uv run pytest tests/test_kb_wpl_01_7_capability_mapping.py -q
```
