# Integration I3 — Investigation Domain Audit

**Status:** completed locally (Option B — adapters + projections)  
**Decision:** adapters reuse existing Project / Campaign / Supervisor / Skill surfaces; **no** Investigation aggregate migration in I3.  
**Additive Option C** documented for later approval — see [integration_i3_investigation_api.md](integration_i3_investigation_api.md).

## Baseline

```
git branch: master
git log tip: 0524316 chore: checkpoint Product Alpha A1-A6 …
```

Checks run: I1/I2 selfchecks, verdict-readiness selfcheck, supervisor regression (AI.254), CC regression (AI.164), Project API tests.

## Direct inventory answers

| Question | Answer |
|----------|--------|
| Investigation entity on backend? | **No** |
| EvidenceRecord persisted? | **No** (Architecture V2.1 mapping: absent) |
| Typed InvestigationSource? | **No** |
| Can adapters alone provide SoT for evidence/findings? | **No** |
| I3 choice | **Option B** — projections + honest gaps; Option C design only |

## Major backend surfaces (summary)

| Surface | API | Persistence | Match to Investigation |
|---------|-----|-------------|------------------------|
| Project | `/projects/{id}` | DB | Context only — exact for project load |
| Campaign Control Center | `.../control-center` | Derived | Timeline / health — partial, campaign ops |
| Campaign Supervisor | `.../supervisor-report` | Derived | Quality findings — **incompatible** as Evidence |
| Marketing skill runs | `.../marketing-skills/runs` | DB | Research artifact candidates — partial |
| Marketing specialist outputs | plan execution | DB | Desk research content — partial text, not evidence graph |
| Agent runs / LLM requests | `/agent-runs`, `/llm-requests` | DB | Telemetry — **incompatible** as Source/Evidence |
| Tasks | `/tasks` | DB | Generic work — weak |
| Execution readiness | readiness APIs | Derived | **incompatible** vs verdict readiness |

## Why not Option A alone for product SoT

Adapters cannot guarantee: Investigation lifecycle, Source identity, Evidence with citations, Finding resolution, Contradiction workflow, RiskItem, Verdict readiness API.

## Why not Option C migration in I3

1. Full Source→Evidence→Finding stack needs careful contracts (risk of fake SoT).
2. Semantic collision with `CampaignSupervisorFinding` must stay firewalled.
3. TZ: do not implement all artifact tables automatically; produce gap report first.
4. Outcomes 1–7, 9–10 achieved by projections without schema change.

## Blocker for durable Investigation SoT (I3+)

Without additive `Investigation` + `InvestigationSource` + `InvestigationEvidence` (or approved equivalent), Product Alpha cannot persist investigation versions or confirmed evidence across devices. **Recommended after I4 semantics settle**, not silent JSON dump on Project.config.

## Stop conditions — none triggered

No Runtime rewrite, no AgentType change, no second research engine, ownership via existing Project APIs preserved.
