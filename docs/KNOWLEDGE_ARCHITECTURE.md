# KNOWLEDGE ARCHITECTURE

**Phase:** AI.255.1 — Knowledge Import Foundation

---

## Layer model

```
Knowledge
   ↓
Skill
   ↓
Workflow
   ↓
Tool
   ↓
Campaign
   ↓
Business Operator
```

BotFazer = **Agent Operating System**

```
Agent =
  Instructions
+ Knowledge
+ Skills
+ Tools
+ Memory
+ Workflows
+ Supervisor
```

**Knowledge Governance** (ADR-KG-001) layers lifecycle, Semantic Chunk, Benchmark, Citation Contract, and freshness on top of this foundation — without VectorDB/LLM retrieval in the architecture landing phase. See [knowledge_governance_subsystem.md](knowledge_governance_subsystem.md).

---

## Repository layout (imported)

| Path | Role |
|------|------|
| `knowledge/` | Domain facts, prompts, manuals, topical research (Wordstat, Metrica, offers, content…) |
| `skills/` | Skill bundles (`SKILL.md`, `references/`, `examples/`, `templates/`) |
| `workflows/raw/` | Legacy n8n/Make workflow JSON — **archive, not runtime** |
| `workflows/mapped/` | Future BotFazer-native process templates |
| `standards/` | Operating standards (memory, skills, tools, commands, supervisor, workflows) |
| `knowledge_import/` | Staging mirror of external sources |

---

## Product mapping (existing code)

| Imported layer | BotFazer implementation today |
|----------------|------------------------------|
| Knowledge | `knowledge/*` corpus (new) + campaign brief/intent |
| Skill | `app/marketing/skills/registry.py`, `MarketingSkillType` |
| Workflow | `app/marketing/workflows/registry.py`, `CampaignWorkflowTemplate` |
| Tool | `MarketingToolType`, data tools v1 |
| Campaign | Business Campaign Layer + Control Center |
| Supervisor | `campaign_supervisor_engine` (read-only) |
| Business Operator | Rule-based intent → scenario → campaign |

---

## Strategic vision (preserve)

- BotFazer **is not** a chatbot.
- BotFazer **is not** an agent constructor.
- Goal: **fully replace a marketing agency** with an operating system for campaigns.

Imported knowledge supports that vision by separating:

1. **Reference corpus** (what we know)
2. **Executable contracts** (what the product runs — explicit, tested, no auto-import)

---

## Guardrails

- No automatic execution of imported n8n JSON
- No changes to `app/`, migrations, API, DB, or tests in AI.255.1
- Mapping from `workflows/raw/` → product registry is a **later, curated** phase
