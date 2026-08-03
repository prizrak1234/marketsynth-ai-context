# Knowledge Linking

**Skill ID:** `ms.skill.knowledge_linking` v0.1.0 candidate non-executable.

Analyze bounded Marketsynth knowledge metadata and produce a reviewable Knowledge
Linking Report. Proposes links — never applies them.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Broken/orphan/duplicate/supersession/contradiction detection | Filesystem editing |
| Link proposals with provenance | Markdown rewriting |
| Index recommendations | Record merge/delete |
| Tenant boundary enforcement | Database/graph persistence |

## Frozen knowledge consumption

Reads Workflow Pattern Library index, Skill registry metadata, PracticeRecords,
and related artifacts as **read-only metadata** — no raw file bodies.

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_5_knowledge_linking_skill.py -q
```
