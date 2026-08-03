# ms.skill.presentation_architecture

**Version:** 0.1.0  
**Status:** Frozen candidate (KB-WPL-01.6)  
**output_contract_type:** `research`  
**executable:** `false`

## Purpose

Transform approved source content into an evidence-aware, provider-neutral presentation
specification: narrative arc, slide plan, visual/chart briefs, theme recommendations,
accessibility controls, and claim safety findings.

## Boundaries

| In scope | Out of scope |
|----------|--------------|
| Presentation specification | Marp/PPTX/PDF rendering |
| Slide sequence and objectives | Canva / Google Slides integration |
| Visual and chart briefs | Image/chart generation |
| Theme/typography direction | File export or publication |
| Evidence and claim safety | Connector execution |

## Input highlights

Requires presentation objective, type, audience, source references, language, tone, and
delivery context. Positioning/Offer references optional for internal/technical/research
materials. Rejects raw secrets, executable content, CSS/HTML injection, and unsupported
customer-facing claims marked as approved.

## Output highlights

Produces `presentation_readiness`, `slide_plan`, `narrative_arc`, `visual_briefs`,
`chart_requirements`, `theme_recommendation`, `accessibility_requirements`, and
`renderer_requirements` — never rendered files or provider design IDs.

## Knowledge sources (read-only)

Approved source content, evidence references, marketing claims (when present), frozen
Workflow Pattern Library, optional Knowledge Linking reports.

## Regression

```bash
uv run pytest tests/test_kb_wpl_01_6_presentation_architecture_skill.py -q
```

## Freeze audit

[KB-WPL-01.6-presentation-architecture-freeze-audit.md](../rfc/KB-WPL-01.6-presentation-architecture-freeze-audit.md)
