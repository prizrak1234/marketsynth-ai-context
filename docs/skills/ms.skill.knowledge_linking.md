# ms.skill.knowledge_linking

**Version:** 0.1.0  
**Status:** Frozen candidate (KB-WPL-01.5)  
**output_contract_type:** `research`  
**executable:** `false`

## Purpose

Analyze bounded Marketsynth knowledge metadata and produce a reviewable Knowledge
Linking Report with proposed links, broken-link findings, orphan/duplicate/supersession/
contradiction candidates, and index recommendations.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Link proposals with provenance | Filesystem editing |
| Broken/orphan/duplicate detection | Record merge/delete |
| Tenant boundary enforcement | Database/graph persistence |
| Index recommendations | Automatic link insertion |

## Knowledge sources (read-only)

Skill registry metadata, Workflow Pattern Library index, PracticeRecords, RFC metadata,
capability maps, lineage and audit references.

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_5_knowledge_linking_skill.py -q
```

## Freeze audit

[KB-WPL-01.5-knowledge-linking-freeze-audit.md](../rfc/KB-WPL-01.5-knowledge-linking-freeze-audit.md)
