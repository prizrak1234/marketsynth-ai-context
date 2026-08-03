# Agent OS Architecture

BotFazer is an **Agent Operating System** — a structured runtime for business marketing, not a bag of prompts.

Substantial product capabilities must also follow the **[Marketsynth Subsystem Standard](architecture/marketsynth_subsystem_standard.md)** (lifecycle, operator, manifest, readiness, honest capability). Subsystems extend this Agent OS — they do not create a second Runtime.

Platform-level orchestration: **[MARKETSYNTH-OPERATING-MODEL.md](MARKETSYNTH-OPERATING-MODEL.md)** (Observe → Research → Reason → Approve → Execute → Measure → Learn).

## Core equation

```
Agent =
  Instructions
+ Knowledge
+ Skills
+ Tools
+ Memory
+ Workflows
+ Commands
+ Supervisor
```

## Layer definitions

| Layer | Role | BotFazer today |
|-------|------|----------------|
| **Instructions** | How the agent behaves, output format, guardrails | System prompts, operator rules, `CURSOR_OPERATING_RULES.md` |
| **Knowledge** | Domain facts, frameworks, prompts, manuals | `knowledge/`, campaign brief, skill context summaries |
| **Skills** | Professional processes with inputs/outputs | `MarketingSkillType`, skill registry, explicit skill runs |
| **Tools** | Atomic capabilities (API calls, generators) | `MarketingToolType`, Wordstat / Metrica / image gen |
| **Memory** | Persistent context across sessions | Project/campaign metadata, skill context on campaign |
| **Workflows** | Reusable business process templates | `CampaignWorkflowTemplate`, checklist runs (no auto-run) |
| **Commands** | Explicit user-triggered actions | Campaign Action Center, wizard advance, approvals |
| **Supervisor** | Read-only quality control | Gaps, contradictions, risks → recommended actions |

## Dependency direction

```
Knowledge
  ↓ informs
Skill
  ↓ may use
Tool
  ↓ produces artifacts inside
Workflow (checklist)
  ↓ inside
Campaign
  ↓ orchestrated by
Business Operator
```

Skills **compose** tools. Workflows **recommend** skills and actions. Supervisor **never executes** — it only reports.

## Skills vs tools vs workflows

### Skills — professional processes

- Example: segment research, offer packaging, Wordstat research.
- Have required inputs, structured outputs, out-of-scope boundaries.
- Run **one at a time**, explicitly, via API or Action Center.
- Merge safe summaries into campaign `skill_context`.

### Tools — atomic capabilities

- Example: Wordstat query, Metrica pull, image generation.
- No business narrative alone — skills wrap them with process.
- Never auto-invoked; logged and sanitized.

### Workflows — reusable business processes

- Example: `lead_gen_campaign`, `content_machine`, `offer_validation`.
- Registry of steps that **recommend** existing actions/skills.
- `CampaignWorkflowRun` = checklist state only — **not** n8n execution.

## Supervisor

Read-only controller:

- Health score, findings (critical / warning / info).
- Missing inputs, contradictions, risks.
- May link findings to `CampaignActionType` — user runs explicitly.
- No LLM requirement in v1; rule-based is valid.

## Agent OS vs chat

| Chat product | BotFazer Agent OS |
|--------------|-------------------|
| Message in → message out | Goal in → campaign state + next action |
| User picks tools | System recommends; user confirms |
| Stateless or ad-hoc | Brief, artifacts, timeline, provenance |
| "Help me write copy" | "Run lead gen for dental clinic" → full conveyor |

## Extension rules

1. New capability → contract in `app/schemas/contracts.py` first.
2. Skills and workflows stay **registries** until a phase explicitly adds execution.
3. Frozen layers (pipeline, publishing, supervisor v1…) are extended, not rewritten.
4. Imported n8n JSON lives in `workflows/raw/` — never wired directly to runtime.

## Related docs

- [PROJECT_VISION.md](PROJECT_VISION.md)
- [KNOWLEDGE_ARCHITECTURE.md](KNOWLEDGE_ARCHITECTURE.md)
- [MARKETING_AGENT_TARGET_MODEL.md](MARKETING_AGENT_TARGET_MODEL.md)
