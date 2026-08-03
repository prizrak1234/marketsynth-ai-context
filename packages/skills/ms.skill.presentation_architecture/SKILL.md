# Presentation Architecture

**Skill ID:** `ms.skill.presentation_architecture` v0.1.0 candidate non-executable.

Transform approved source content into a **provider-neutral presentation specification**.
No Marp, PowerPoint, PDF, Canva or Google Slides rendering in this phase.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Narrative arc and slide plan | Slide rendering |
| Visual/chart/image briefs | Image/chart generation |
| Theme/typography recommendations | File export |
| Evidence and claim safety review | Publication |

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_6_presentation_architecture_skill.py -q
```
