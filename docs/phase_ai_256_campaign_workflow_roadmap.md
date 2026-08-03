# Phase AI.256 — Campaign Workflow Roadmap

**Goal:** Turn `workflows/raw` archive into a managed **Campaign Workflow Layer** — curated `CampaignWorkflowTemplate` in product, not n8n execution.

## Not in v1

- n8n / Make execution
- Auto-run of steps
- Background workers
- External provider calls from import
- LangGraph / agent executors

## v1 scope (AI.256–AI.265)

| Phase | Deliverable |
|-------|-------------|
| AI.256 | This roadmap |
| AI.257 | Raw workflow inventory index (`docs/WORKFLOW_RAW_INVENTORY.md`, `workflows/mapped/raw_inventory_index.json`) |
| AI.258 | `CampaignWorkflowTemplate` contract (+ run, step, suggestion types) |
| AI.259 | Curated registry v1 — 5 templates in `app/marketing/workflows/registry.py` + `workflows/mapped/curated_templates.json` |
| AI.260 | Recommendation engine (scenario, brief, supervisor, skills, artifacts) — read-only |
| AI.261 | `CampaignWorkflowRun` persistence (`campaign_workflow_runs`) |
| AI.262 | Workflow API — list templates, create run (no step execution) |
| AI.263 | Step mapping → existing `CampaignActionType` / skills |
| AI.264 | Control Center UI + regression tests |
| AI.265 | Freeze audit + docs |

## Layer model

```
workflows/raw/     → archive (1700+ JSON) — inventory only
workflows/mapped/  → curation manifest + future template mappings
app/.../registry → product CampaignWorkflowTemplate (5 v1)
```

## Registry templates (v1)

| id | Purpose |
|----|---------|
| `lead_gen_campaign` | Segment → demand → offer → content → publication |
| `content_machine` | Meaning → offer → content → media → publication |
| `offer_validation` | Segment → offer → justification → Wordstat |
| `metrica_traffic_diagnostics` | Metrica → Wordstat |
| `visual_content_pack` | Visual report → media brief → publication |

## Invariants

- Recommendations read-only until user starts a checklist run
- `create-run` inserts workflow run row only
- Supervisor findings may elevate workflow suggestions
- Raw JSON never wired to runtime automatically

## Next phases (out of scope)

- Populate `representative_raw_samples` in curated manifest
- Manual step completion recording
- Workflow analytics across campaigns

## Regression

```bash
uv run pytest tests/test_phase_ai_264_campaign_workflow_layer_regression.py -q
uv run python scripts/build_workflow_raw_inventory.py
```
