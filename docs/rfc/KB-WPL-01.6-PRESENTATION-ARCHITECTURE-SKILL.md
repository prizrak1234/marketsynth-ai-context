# KB-WPL-01.6 — Presentation Architecture Skill

| Field | Value |
|-------|-------|
| **Program** | KB-WPL-01.6 |
| **Status** | **READY** — frozen candidate non-executable Skill |
| **Skill** | `ms.skill.presentation_architecture` v0.1.0 |
| **Depends on** | KB-WPL-01.3C (frozen WPL), KB-WPL-01.5 (Knowledge Linking) |

## 1. Executive verdict

**READY.** Native Presentation Architecture Skill transforms approved source content into
an evidence-aware, provider-neutral **presentation specification**. It designs narrative
structure, slide sequence, visual/chart briefs, theme recommendations, accessibility
controls, and claim safety findings — but does **not** render Marp, PowerPoint, PDF,
Canva, or Google Slides.

## 2. Package identity

| Field | Value |
|-------|-------|
| Package hash | `60ce698336fa21006ba203472fc6c3cef5661171ec2e45b641dcca743a42e95c` |
| executable | false |
| production_eligible | false |
| runtime_authorized | false |
| freeze_status | frozen_candidate |
| output_contract_type | research |

## 3. Architectural boundary

| In scope | Out of scope |
|----------|--------------|
| Presentation specification | Slide rendering |
| Narrative arc and slide plan | PPTX/PDF/Marp export |
| Visual/chart/image briefs | Image/chart generation |
| Theme/typography recommendations | Provider credential selection |
| Evidence and claim safety review | Publication or asset upload |
| Accessibility requirements | Connector execution |

Renderer selection belongs to future Connector and Execution layers.

## 4. Presentation types

Finite taxonomy: `business_pitch`, `sales_presentation`, `investor_presentation`,
`market_research_report`, `strategy_presentation`, `project_status`, `technical_architecture`,
`training`, `internal_decision`, `case_study`, `product_demo_structure`, `webinar`,
`conference_talk`, `content_carousel_source`, `custom`.

Positioning/Offer references optional for internal, technical, research, and training use cases.

## 5. Schema models

| Schema | Purpose |
|--------|---------|
| `narrative-arc.schema.json` | Narrative arc with evidence development and CTA |
| `slide-specification.schema.json` | Slide sequence with one primary message per slide |
| `content-block.schema.json` | Structured content blocks (no HTML/CSS) |
| `visual-brief.schema.json` | Renderer-neutral visual briefs |
| `chart-requirement.schema.json` | Data-referenced chart requirements |
| `theme-recommendation.schema.json` | Provider-neutral theme direction |

## 6. Claim and evidence safety

- Source claims retain evidence references.
- Unsupported claims remain visible; cannot become key messages.
- Prohibited claims rejected at input.
- Financial projections require source and assumptions for investor presentations.
- Statistics require source/date/scope.
- Skill cannot upgrade a claim's substantiation status.

## 7. Workflow pattern references (read-only)

May reference: `source_lineage_preservation`, `quality_gate_after_generation`,
`draft_to_human_approval`, `human_edit_then_resume`, `evidence_grounded_generation`.
PatternSelectionReference preserves library version, semantic hash, maturity, and
`runtime_authorized=false`.

## 8. Methodology source

Adapted presentation hierarchy methodology from external archive (`skills.zip → marp-slide/`)
— narrative planning, slide-density rules, theme-selection logic, visual hierarchy, and QA
checklist only. No external CSS/templates imported as authoritative Marketsynth assets.

## 9. Legacy linking module note (governance)

- `app/knowledge/knowledge_linking/` — **authoritative** for KB-WPL-01.5.
- `app/knowledge/linking/` — **legacy**; do not add new imports; removal deferred.

## 10. Verification

```bash
uv run pytest tests/test_kb_wpl_01_5_knowledge_linking_skill.py -q
uv run pytest tests/test_kb_wpl_01_6_presentation_architecture_skill.py -q
uv run ruff check \
  app/knowledge/presentation_architecture \
  tests/test_kb_wpl_01_6_presentation_architecture_skill.py \
  tests/support/presentation_architecture_skill_validation.py
```

## 11. Related

- [Skill doc](../skills/ms.skill.presentation_architecture.md)
- [Freeze audit](./KB-WPL-01.6-presentation-architecture-freeze-audit.md)
- [Knowledge Linking Skill](./KB-WPL-01.5-KNOWLEDGE-LINKING-SKILL.md)
- [Workflow Pattern Library v0.1.0](../architecture/WORKFLOW-PATTERN-LIBRARY-v0.1.0.md)

## 12. Next queue

| Phase | Deliverable |
|-------|-------------|
| KB-WPL-01.7 | Profession / Capability / Skill / Pattern Mapping |
| KB-WPL-01.8 | Knowledge Discovery Read Models |
| KB-WPL-01.9 | Integrated Freeze Audit |
